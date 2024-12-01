import time
import json
import os
import logging
from driver.utils.dbops import get_recent_unprocessed_posts_by_domain, mark_posts_as_processed, save_summary_to_db
from jinja2 import Template

logger = logging.getLogger(__name__)


def process_posts(limit=None, summaries_file=None, client=None, configuration=None):
    def restructure_summaries(summaries):
        category_bag = {}
        for summary in summaries:
            category = summary.get('category', 'uncategorized').lower()
            text_summary = summary.get('summary', '')
            
            if category not in category_bag:
                category_bag[category] = []
            
            category_bag[category].append({
                'url': summary['url'],
                'title': summary['title'],
                'domain': summary['domain'],
                'summary': text_summary
            })
        return category_bag
    
    
    def filter_invalid_summaries(summaries_bag):
        filtered_bag = {}
        for category, summaries in summaries_bag.items():
            if category.lower() not in [c.lower() for c in configuration.get('categories', [])]:
                logger.warning(f"Filtered out invalid category: {category}")
                continue
            
            valid_summaries = []
            for summary in summaries:
                if "Unfortunately, no content was provided to summarize or categorize" in summary.get('summary', ''):
                    logger.warning(f"Filtered out invalid summary - Domain: {summary.get('domain')}, URL: {summary.get('url')}")
                else:
                    valid_summaries.append(summary)
            
            if valid_summaries:
                filtered_bag[category] = valid_summaries
        
        return filtered_bag
    def process_single_post(post):
        def create_result(summary, category):
            return {
                "url": post.get('url'),
                "title": post.get('title'),
                "subtitle": post.get('subtitle'),
                "domain": post.get('domain'),
                "date": post.get('date'),
                "summary": summary,
                "category": category
            }
        

        user_prompt_template = Template(configuration.get('user_prompt', ''))
        user_prompt = user_prompt_template.render(categories=configuration.get('categories', []), post=post)

        system_prompt_template = Template(configuration.get('system_prompt', ''))
        system_prompt = system_prompt_template.render()
        
        response = client.generate_completion(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=configuration.get('temperature', 0.7),
            max_tokens=configuration.get('max_tokens', 500)
            )
        logger.debug(f"Response: {response}")
        
        try:
            # Remove markdown json code block wrappers if they exist
            content = response.get('content', '').strip()
            if content.startswith('```json'):
                content = content[7:]  # Remove ```json prefix
            if content.endswith('```'):
                content = content[:-3]  # Remove ``` suffix
            parsed_content = json.loads(content)
            if 'error' in parsed_content and parsed_content['error'] is not None and parsed_content['error'] != '':
                logger.error(f"Error in response for {post.get('url')}: {parsed_content['error']}")
                return None
            result = create_result(parsed_content.get('summary', ''), parsed_content.get('category', ''))
            logger.info(f"Domain: {post.get('domain')} | Url: {post.get('url')} | Summary: {result['summary']}")
            return result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response for {post.get('url')}. Initial content: {response.get('content', '')}")
            return None
    
    unprocessed_posts = get_recent_unprocessed_posts_by_domain()
    logger.info(f"Unprocessed posts length: {len(unprocessed_posts)}")
    summaries = list()
    logger.info(f"Summary limit: {limit}")
    for post in unprocessed_posts[:limit] if limit else unprocessed_posts:
        result = process_single_post(post)
        if result:
            summaries.append(result)
            save_summary_to_db(result)

    # Restructure summaries into a category bag
    category_bag = restructure_summaries(summaries)
    # Replace the original summaries list with the category bag
    urls_to_mark = [post['url'] for post in unprocessed_posts]
    mark_posts_as_processed(urls_to_mark)
    filtered_category_bag = filter_invalid_summaries(category_bag)
    
    # Write the filtered category bag to summaries.json
    with open(summaries_file, 'w') as f:
        json.dump(filtered_category_bag, f, indent=4)
    
