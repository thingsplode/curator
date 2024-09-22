import logging
import logging.config
import os, argparse
import json
from driver.agents import process_unprocessed_posts
from driver.scrapers.substack import scrape_substack
from driver.utils.utils import generate_html_summary

project_root = os.path.dirname(os.path.abspath(__file__))
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            # 'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'format': '%(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['default'],
            'level': 'WARNING',
            'propagate': True
        },
        'main': {  # logger for the current file
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        },
        '__main__': {  # logger for the main module
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        },
        'driver': {  # project-specific logger
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
})
logger = logging.getLogger(__name__)


# logging.basicConfig(
#     # level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )
# logger.setLevel(logging.DEBUG)

# for name in logging.root.manager.loggerDict:
#     print(f'logger name {name} for project root {os.path.basename(project_root)}')
#     if name.startswith(os.path.basename(project_root)):
#         logging.getLogger(name).setLevel(logging.DEBUG)

def main():
    try:
        # Get the current working directory
        current_working_directory = os.getcwd()
        logger.info(f"Current working directory: {current_working_directory}")


        # Set up argument parser
        parser = argparse.ArgumentParser(description='Scrape and process Substack posts.')
        parser.add_argument('posts_to_scrape', type=int, default=5, help='Number of posts to scrape', nargs='?')
        parser.add_argument('posts_to_process', type=int, default=5, help='Number of posts to process', nargs='?')
        args = parser.parse_args()
        logger.info(f"Number of posts to process: {args.posts_to_scrape}")

        logger.debug('Start scraping')
        substacks = ['https://www.leahtharin.com/', 
                     'https://www.growthunhinged.com/', 
                     'https://katesyuma.substack.com/',
                     'https://www.news.aakashg.com/',
                     'https://www.howtheygrow.co/',
                     'https://www.lennysnewsletter.com/',
                     'https://dpereira.substack.com/',
                     'https://lg.substack.com/',
                     'https://www.productcompass.pm/',
                     'https://productify.substack.com/',
                     'https://newsletter.mkt1.co/',
                     'https://handpickedberlin.substack.com/',
                     'https://www.proofofconcept.pub/',
                     ]
        # scrape_substack(substacks, 
        #                 working_dir=current_working_directory,
        #                 project_dir=project_root,
        #                 num_posts_to_scrape=args.posts_to_scrape, 
        #                 authentication={'email': os.environ.get('SUBSTACK_EMAIL'), 'password': os.environ.get('SUBSTACK_PASSWORD')})
        summaries_bag = process_unprocessed_posts(limit=args.posts_to_process)
        # summaries_bag = {
        #     "go to market": [
        #         {
        #             "url": "https://www.growthunhinged.com/p/your-guide-to-gtm-metrics-20",
        #             "title": "Your guide to GTM metrics 2.0",
        #             "domain": "growthunhinged",
        #             "summary": ""
        #         },
        #         {
        #             "url": "https://www.leahtharin.com/p/72-rand-fishkin-why-paid-advertising",
        #             "title": "72: Rand Fishkin - Why paid advertising sucks in 2024",
        #             "domain": "leahtharin",
        #             "summary": ""
        #         }
        #     ],
        #     "people management": [
        #         {
        #             "url": "https://handpickedberlin.substack.com/p/issue113",
        #             "title": "the most annoying colleague...",
        #             "domain": "handpickedberlin",
        #             "summary": "This community newsletter covers a range of topics from mentorship, street art events, to tech jobs, and interesting Berlin-based startups. Join in the discussions, check out available jobs, and learn about recently funded companies. Also, get a sneak-peek into the daily routines of famous personalities."
        #         }
        #     ],
        #     "invalid": [
        #         {
        #             "url": "https://katesyuma.substack.com/podcast",
        #             "title": "",
        #             "domain": "katesyuma",
        #             "summary": "Unfortunately, no content was provided to summarize or categorize. Please provide valid blog-post content."
        #         }
        #     ],
        #     "leadership": [
        #         {
        #             "url": "https://www.leahtharin.com/p/71-john-cutler-how-to-structure-a",
        #             "title": "71: John Cutler - How to structure a product organization",
        #             "domain": "leahtharin",
        #             "summary": ""
        #         }
        #     ]
        # }
        logger.debug(json.dumps(summaries_bag, ensure_ascii=False, indent=4))
        generate_html_summary(summaries_bag)
        
    except Exception as e:
        logger.error(e, stack_info=True, exc_info=True)
        exit(-1)
if __name__ == "__main__":
    main()

