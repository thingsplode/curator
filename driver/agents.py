import time
import autogen
import json
import os
import logging
from driver.utils.dbops import get_recent_unprocessed_posts_by_domain, mark_posts_as_processed
from openai import OpenAI

logger = logging.getLogger(__name__)
categories = [
    'product design', 'product culture', 'leadership', 'people management', 'technical', 'product hack', 'go to market', 'sales', 'data analysis', 'data driven decision making', 'uncategorized'
]

def process_unprocessed_posts(limit=None, summaries_file=None):
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
            if category.lower() not in [c.lower() for c in categories]:
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
        
        prompt = f"Write a short and engaging summary of the following markdown content in 2 to 3 lines. Ensure that the symmary includes 1-2 key insights and provides a compelling reason to read the full article.\
        Categorize the post into one of the following categories: \
        { ', '.join(categories)}. \
        Return a structured answer in JSON format, separating the summary, the category and anoptional error only in case you cannot fulfill the task:\n\n{post.get('md')}"
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert copywriter and journalist. Your task is to write a TL;DR style newsletter by summarizing blog-posts and intrigue the reader to click on the link and read the full article."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
            )
        logger.debug(f"Response: {response}")
        response_content = response.choices[0].message.content.strip()
        # Rate limiting: 10000 tokens per minute
        tokens_used = response.usage.total_tokens
        sleep_time = tokens_used / 10000
        logger.debug(f"Sleeping for {sleep_time} seconds")
        time.sleep(sleep_time)  # Sleep for a fraction of a minute based on tokens used
        try:
            parsed_content = json.loads(response_content)
            if 'error' in parsed_content and parsed_content['error'] is not None and parsed_content['error'] != '':
                logger.error(f"Error in response for {post.get('url')}: {parsed_content['error']}")
                return None
            result = create_result(parsed_content.get('summary', ''), parsed_content.get('category', ''))
            logger.info(f"Domain: {post.get('domain')} | Url: {post.get('url')} | Summary: {result['summary']}")
            return result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response for {post.get('url')}. Initial content: {response_content}")
            return None
    
    try:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    except KeyError as e:
        raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it before running the script.")
    
    unprocessed_posts = get_recent_unprocessed_posts_by_domain()
    logger.debug(f"Unprocessed posts length: {len(unprocessed_posts)}")
    summaries = list()
    logger.debug(f"Summary limit: {limit}")
    for post in unprocessed_posts[:limit] if limit else unprocessed_posts:
        result = process_single_post(post)
        if result:
            summaries.append(result)

    # Restructure summaries into a category bag
    category_bag = restructure_summaries(summaries)
    # Replace the original summaries list with the category bag
    urls_to_mark = [post['url'] for post in unprocessed_posts]
    mark_posts_as_processed(urls_to_mark)
    filtered_category_bag = filter_invalid_summaries(category_bag)
    
    # Write the filtered category bag to summaries.json
    with open(summaries_file, 'w') as f:
        json.dump(filtered_category_bag, f, indent=4)
    
