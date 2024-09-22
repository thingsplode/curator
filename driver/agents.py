import time
import autogen
import json
import os
import logging
from driver.utils import get_recent_unprocessed_posts_by_domain, mark_posts_as_processed
from openai import OpenAI

logger = logging.getLogger(__name__)
categories = [
    'product design', 'product culture', 'leadership', 'people management', 'technical', 'product hack', 'go to market', 'sales', 'data analysis', 'data driven decision making'
]
# class SummaryAgent(autogen.AssistantAgent):
#     def __init__(self):
#         super().__init__(
#             name="SummaryAgent",
#             system_message="You are an expert copywriter and journalist, good at writing short, engaging summaries of blog posts. You're tasked to write a TL;DR style newletter by summarizing interesting posts from a given list.",
#             llm_config={
#                 "temperature": 0.7,
#                 "max_tokens": 150,
#                 "config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}],
#             }
#         )

#     def summarize_post(self, content):
#         prompt = f"Write a short and engaging summary of the following content in 2 lines:\n\n{content}"
#         response = self.initiate_chat(prompt)
#         print(f'response: {response}')
#         return response['content'].strip()  # Extracting content from the response

# def process_unprocessed_posts():
#     summary_agent = autogen.AssistantAgent(
#         name="SummaryAgent",
#         system_message="You are an expert copywriter and journalist, good at writing short, engaging summaries of blog posts. You're tasked to write a TL;DR style newletter by summarizing interesting posts from a given list.",
#         llm_config={
#             "temperature": 0.7,
#             "max_tokens": 150,
#             "config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}],
#         }
#     )
#     user_proxy = autogen.UserProxyAgent(name="Human", human_input_mode="NEVER", code_execution_config=False)

#     print(f"Unprocessed posts length: {len(unprocessed_posts)}")
#     for post in unprocessed_posts:
#         prompt = f"Write a short and engaging summary of the following content in 2 lines:\n\n{post.get('md')}"
#         chat_result = user_proxy.initiate_chat(summary_agent, message=prompt)
#         # summary = summary_agent.summarize_post(post.get('md'))
#         # print(f"Summary for {post['url']}:\n{summary}\n")
#         print(f"Chat result: {chat_result}")
    
#     # Mark posts as processed
#     urls_to_mark = [post['url'] for post in unprocessed_posts]
#     mark_posts_as_processed(urls_to_mark)

def process_unprocessed_posts(limit=None):
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
                "domain": post.get('domain'),
                "summary": summary,
                "category": category
            }
        
        prompt = f"Write a short and engaging summary of the following content in 2 lines. Categorize the post into one of the following categories: \
        {", ".join(categories)}. \
        Return a structure answer in JSON format, separating the text summary and the category:\n\n{post.get('md')}"
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert copywriter and journalist. Your task is to write a TL;DR style newsletter by summarizing blog-posts and intrigue the reader to click on the link and read the full article."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
            )
        response_content = response.choices[0].message.content.strip()
        try:
            parsed_content = json.loads(response_content)
            result = create_result(parsed_content.get('summary', ''), parsed_content.get('category', ''))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from response for {post.get('url')}")
            result = create_result(response_content, "uncategorized")
        logger.debug(f"Domain: {post.get('domain')} | Url: {post.get('url')} | Summary: {result['summary']}")
        
        # Rate limiting: 10000 tokens per minute
        tokens_used = response.usage.total_tokens
        sleep_time = tokens_used / 10000
        logger.debug(f"Sleeping for {sleep_time} seconds")
        time.sleep(sleep_time)  # Sleep for a fraction of a minute based on tokens used
        
        return result
    
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    
    unprocessed_posts = get_recent_unprocessed_posts_by_domain()
    print(f"Unprocessed posts length: {len(unprocessed_posts)}")
    summaries = list()
    logger.debug(f"Summary limit: {limit}")
    for post in unprocessed_posts[:limit] if limit else unprocessed_posts:
        summaries.append(process_single_post(post))

    # Restructure summaries into a category bag
    category_bag = restructure_summaries(summaries)
    # Replace the original summaries list with the category bag
    urls_to_mark = [post['url'] for post in unprocessed_posts]
    mark_posts_as_processed(urls_to_mark)
    return filter_invalid_summaries(category_bag)
