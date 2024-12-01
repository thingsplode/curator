import logging
import logging.config
import os, argparse
import json
from driver.agents import process_posts
from driver.client import AIClient
from driver.utils.dbops import initialize_db
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

def load_configuration():
        # Read substacks from configuration file
        config_file = f'{project_root}/etc/config.json'
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded configuration from {config_file}")
                return config
        except FileNotFoundError as x:
            logger.error(f"Configuration file {config_file} not found")
            raise x
        except json.JSONDecodeError as x:
            logger.error(f"Error parsing {config_file}. Make sure it's valid JSON")
            raise x

def scrape_substacks(configuration: dict, posts_to_scrape: int):
    substacks = configuration.get('scrapers', {}).get('substacks', [])
    scrape_substack(substacks,
                        project_dir=project_root,
                        num_posts_to_scrape=posts_to_scrape, 
                        authentication={'email': os.environ.get('SUBSTACK_EMAIL'), 'password': os.environ.get('SUBSTACK_PASSWORD')})

def set_log_level(log_level: str):
    log_level = getattr(logging, log_level.upper())
    logging.getLogger('main').setLevel(log_level)
    logging.getLogger('driver').setLevel(log_level)
    logging.getLogger('driver.scrapers').setLevel(log_level)
    logging.getLogger('driver.utils').setLevel(log_level)
    logging.getLogger('driver.agents').setLevel(log_level)
    logging.getLogger('driver.client').setLevel(log_level)
    logger.info(f"Log level set to {log_level}")

def main():
    try:
        # Get the current working directory
        current_working_directory = os.getcwd()
        logger.info(f"Current working directory: {current_working_directory}")
        project_root = os.path.dirname(os.path.abspath(__file__))# Set up argument parser
        parser = argparse.ArgumentParser(description='Scrape and process Substack posts.')
        parser.add_argument('--posts_to_scrape', type=int, default=5, help='Number of posts to scrape', nargs='?')
        parser.add_argument('--posts_to_process', type=int, default=5, help='Number of posts to process', nargs='?')
        parser.add_argument('--steps', nargs='+', default=['all'], choices=['all', 'scrape', 'summarize', 'generate'], 
                            help='Steps to execute. Can be "all", "scrape", "summarize", "generate", or any combination.')
        parser.add_argument('--data_folder', type=str, default=f'{project_root}/data', help='Path to the data folder', nargs='?')
        parser.add_argument('--model', type=str, default='llama3.1', help='Select the model to use. The default is llama3.1', nargs='?')
        parser.add_argument('--client', type=str, default='ollama', help='Select the client to use. The default is ollama', choices=['ollama', 'openai'], nargs='?')
        parser.add_argument('--log-level', type=str, default='INFO', help='Select the log level. The default is INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], nargs='?')
        args = parser.parse_args()
        set_log_level(args.log_level)
        # Ensure the data folder exists
        if not os.path.exists(args.data_folder):
            os.makedirs(args.data_folder)
            logger.info(f"Created data folder: {args.data_folder}")
        else:
            logger.info(f"Existing data folder: {args.data_folder}")

        summaries_file = f'{args.data_folder}/summaries.json'
        database_file = f'{args.data_folder}/media_posts.db'
        
        configuration = load_configuration()
        initialize_db(database_file)

        client = AIClient(client_type=args.client, model=args.model)

        logger.info(f"Steps to execute: {args.steps}")
        logger.info(f"Number of posts to scrape: {args.posts_to_scrape}")
        logger.info(f"Number of posts to process: {args.posts_to_process}")
        
        # Generate a match statement for executing steps based on configuration
        for step in args.steps:
            match step:
                case "scrape" | "all":
                    logger.info('Start scraping')
                    scrape_substacks(configuration, args.posts_to_scrape)
                case "summarize" | "all":
                    logger.info('Start summarizing')
                    process_posts(limit=args.posts_to_process, summaries_file=summaries_file, client=client, configuration=configuration)
                case "generate" | "all":
                    logger.info('Start generating')
                    try:
                        with open(summaries_file, 'r') as f:
                            summaries_bag = json.load(f)
                            if not summaries_bag:
                                raise ValueError("Cannot generate HTML. Please summarize a couple of posts first.")
                            generate_html_summary(summaries_bag, args.data_folder)
                    except FileNotFoundError:
                        logger.error("summaries.json file not found")
                        raise FileNotFoundError("summaries.json file not found. Please ensure the file exists before generating the summary.")
                case _:
                    logger.warning(f"Unknown step: {step}")        
    except Exception as e:
        logger.error(e, stack_info=True, exc_info=True)
        exit(-1)
if __name__ == "__main__":
    # todo: review the titles of the posts in the newsletter (why are they loosing their capitalization?)
    # todo: add the blog title instead of the domain
    # todo: save back the categories to the posts in the database
    main()

