import logging
import os
import json
import requests
import random
from threading import stack_size
from operator import is_not, pos
from functools import partial
from time import sleep
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from datetime import datetime
from driver.utils.dbops import save_posts_to_db, get_existing_urls_for_domain
from driver.utils.utils import html_to_md, TqdmLoggingHandler


# initial source: https://github.com/timf34/Substack2Markdown/blob/main/substack_scraper.py
# todo: refactor to log in only once, no matter how much scraping is happening
# Soup should be created potentially only once

logger = logging.getLogger(__name__)
logger.addHandler(TqdmLoggingHandler())

def scrape_substack(urls: List[str], working_dir: str, project_dir: str, num_posts_to_scrape = None, authentication: dict[str, str] = dict()):
    total = 0
    posts_data = list()
    def get_url_soup(url: str) -> Optional[BeautifulSoup]:
        """
        Gets soup from URL using requests
        """
        try:
            page = requests.get(url, headers=None)
            soup = BeautifulSoup(page.content, "html.parser")
            if soup.find("h2", class_="paywall-title"):
                logger.warning(f'Skipping premium article: {url}')
                return None
            return soup
        except Exception as e:
            raise ValueError(f'Error fetching page: {e}') from e
   
    def get_authenticated_driver():
        logger.debug('authenticating')
        def check_failed_login() -> bool:
            """
            Check for the presence of the 'error-container' to indicate a failed login attempt.
            """
            logger.debug('checking error')
            error_container = driver.find_elements(By.ID, 'error-container')
            if len(error_container) > 0:
                logger.error(error_container[0].text)
            return len(error_container) > 0 and error_container[0].is_displayed()
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        # options.add_argument(f'--user-agent=Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36')
        options.add_argument(f'--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36')
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=en-US")
        logger.debug(f'Initializing driver with path: {project_dir}/chromedriver/chromedriver')
        service = Service(executable_path=f'{project_dir}/chromedriver/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://substack.com/sign-in")
        sleep(3)
        signin_with_password = driver.find_element(
            By.XPATH, "//a[@class='login-option substack-login__login-option']"
        )
        signin_with_password.click()
        sleep(3)
                # Email and password
        email = driver.find_element(By.NAME, "email")
        password = driver.find_element(By.NAME, "password")
        logger.debug(f"email: {authentication.get('email','')}")
        email.send_keys(authentication.get('email',''))
        password.send_keys(authentication.get('password',''))

        # Find the submit button and click it.
        submit = driver.find_element(By.XPATH, "//*[@id=\"substack-login\"]/div[2]/div[2]/form/button")
        sleep(3)
        logger.debug('submitting pass')
        submit.click()
        sleep(5)  # Wait for the page to load

        if check_failed_login():
            raise Exception("Warning: Login unsuccessful. Please check your email and password, or your account status.\n"
                  "Use the non-premium scraper for the non-paid posts. \n"
                  "If running headless, run non-headlessly to see if blocked by Captcha.")
        logger.debug('returning authenticated driver')
        return driver


    def get_authenticated_url_soup(url: str, driver: webdriver.Chrome) -> BeautifulSoup:
        """
        Gets soup from URL using logged in selenium driver
        """
        try:
            driver.get(url)
            return BeautifulSoup(driver.page_source, "html.parser")
        except Exception as e:
            raise ValueError(f"Error fetching page: {e}") from e


    def extract_post_data(soup: BeautifulSoup) -> Tuple[str, str, str, str, str]:
        """
        Converts substack post soup to markdown, returns metadata and content
        """
        title_element = soup.select_one("h1.post-title, h2")
        title = title_element.text.strip() if title_element else "" # When a video is present, the title is demoted to h2

        subtitle_element = soup.select_one("h3.subtitle")
        subtitle = subtitle_element.text.strip() if subtitle_element else ""

        date_selector = ".pencraft.pc-reset._color-pub-secondary-text_3axfk_207._line-height-20_3axfk_95._font-meta_3axfk_131._size-11_3axfk_35._weight-medium_3axfk_162._transform-uppercase_3axfk_242._reset_3axfk_1._meta_3axfk_442"
        date_element = soup.select_one(date_selector)
        date = date_element.text.strip() if date_element else "Date not available"

        like_count_element = soup.select_one("a.post-ufi-button .label")
        like_count = like_count_element.text.strip() if like_count_element else "Like count not available"

        content = str(soup.select_one("div.available-content"))
        md = html_to_md(title, subtitle, date, like_count, content)
        return title, subtitle, like_count, date, md

    def fetch_urls_from_sitemap(url: str) -> List[Tuple[str, Optional[datetime]]]:
        """
        Fetch urls and last modified dates from sitemap.xml
        """
        rsp = requests.get(f'{url}sitemap.xml')
        if not rsp.ok:
            logger.warning(f'Error fetching sitemap at {url}: {rsp.status_code}')
            return list()
        root = ET.fromstring(rsp.content)
        urls_and_dates = []
        for url_element in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc = url_element.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            lastmod = url_element.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
            if loc is not None:
                lastmod_date = None
                if lastmod is not None and lastmod.text:
                    try:
                        lastmod_date = datetime.fromisoformat(lastmod.text.rstrip('Z'))
                    except ValueError:
                        logger.warning(f"Invalid date format for {loc.text}: {lastmod.text}")
                urls_and_dates.append((loc.text, lastmod_date))
        return urls_and_dates
    
    def fetch_urls_from_feed(url: str) -> List[dict]: 
        """
        Fetches URLs from feed.xml.
        """ 
        rsp = requests.get(f'{url}feed.xml')
        if not rsp.ok:
            logger.warning(f'Error fetching feed at {url}: {rsp.status_code}')
            return list()
        root = ET.fromstring(rsp.content)
        return [{'link': getattr(item.find('link'), 'text', None),'date': getattr(item.find('pubDate'),'text', None)} for item in root.findall('.//channel/item') if item is not None]
     
    def scrape_post(post_url, domain, driver):
            try:
                url_leaf = next((item for item in reversed(urlparse(post_url).path.split('/'))), None)
                if url_leaf in ['about', 'archive']:
                    logger.debug(f'Skipping {post_url} as it is not a post (about or archive)')
                    return None
                logger.debug(f'Scraping {post_url}')
                soup = get_authenticated_url_soup(post_url, driver=driver)
                soup = get_url_soup(post_url)
                if soup is None:
                    return 'retry'
                title, subtitle, like_count, date, md = extract_post_data(soup)
                return {
                    'domain': domain,
                    'url': post_url,
                    'title': title,
                    'subtitle': subtitle,
                    'like_count': like_count,
                    'date': date,
                    'md': md
                }
            except Exception as e:
                logger.error(e, stack_info=True, exc_info=True)
                return None
     
    driver = get_authenticated_driver()
    
    # start scraping
    for url in urls:
        url = url if url.endswith('/') else url + '/'
        domain = [p for p in urlparse(url).netloc.split('.') if p != 'www'][0]
        # os.makedirs(f'{working_dir}/{domain}', exist_ok=True) 
        
        sitemap_urls_and_dates: List[Tuple[str, Optional[datetime]]] = fetch_urls_from_sitemap(url)
        logger.debug(f'length of sitemaps for {url}: {len(sitemap_urls_and_dates)}')
        
        # Filter out posts that are already in the database
        
        filtered_sitemap_urls_and_dates = [
            (url, date) for url, date in sitemap_urls_and_dates
            if urlparse(url).path.split('/')[-1] not in ['about', 'archive', 'podcast']
        ]
        

        existing_urls = get_existing_urls_for_domain(domain)
        filtered_sitemap_urls_and_dates = [
            (url, date) for url, date in filtered_sitemap_urls_and_dates
            if url not in existing_urls
        ]
        if len(filtered_sitemap_urls_and_dates) == 0:
            logger.debug(f'No new posts found for {url}. Skipping to next URL.')
            continue

        logger.debug(f'Filtered sitemap URLs for {url}: {len(filtered_sitemap_urls_and_dates)}')
        total = num_posts_to_scrape if num_posts_to_scrape is not None else len(filtered_sitemap_urls_and_dates)
        logger.debug(f'Scraping {total} posts after filtering for {url}.')

        for post_url, post_date in tqdm(filtered_sitemap_urls_and_dates[:total], total=total):
            result = scrape_post(post_url, domain, driver)
            if result == 'retry':
                total += 1
            elif result:
                result['date'] = post_date.isoformat() if post_date else None
                posts_data.append(result)    
            sleep(random.uniform(2, 5))
    
    driver.quit()
    logger.debug('Scraping is finished')

    # Save the scraped posts to the database
    save_posts_to_db(posts_data)
    # print(json.dumps(posts_data, ensure_ascii=False, indent=4))