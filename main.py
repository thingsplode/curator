import logging
import logging.config
import os
import json
from driver.agents import process_unprocessed_posts
from driver.scrapers.substack import scrape_substack
from driver.utils import generate_html_summary

project_root = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger(__name__)

def configure_logging():
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
            'driver': {  # project-specific logger
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': False
            },
        }
    })

configure_logging()


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
        scrape_substack(substacks, '.', 4, {'email':'', 'password':''})
        summaries_bag = process_unprocessed_posts(limit=5)
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

