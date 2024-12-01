import logging
import html2text
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import os
import json


logger = logging.getLogger(__name__)

def html_to_md(title: str, subtitle: str, date: str, like_count: str, html_content: str) -> str:
    """
    This method converts HTML to Markdown
    """
    def combine_metadata_and_content(content: str) -> str:
        """
        Combines the title, subtitle, and content into a single string with Markdown format
        """
        if not isinstance(title, str):
            raise ValueError("title must be a string")

        if not isinstance(content, str):
            raise ValueError("content must be a string")

        metadata = f"# {title}\n\n"
        if subtitle:
            metadata += f"## {subtitle}\n\n"
        metadata += f"**{date}**\n\n"
        metadata += f"**Likes:** {like_count}\n\n"

        return metadata + content
    if not isinstance(html_content, str):
        raise ValueError("html_content must be a string")
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    md_content = h.handle(html_content)
    return combine_metadata_and_content(md_content)

def generate_html_summary(summary_data: dict, data_folder: str):
    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader('etc/templates'))
    template = env.get_template('summary_template.html')

    # Group summaries by category
    categories = {}
    for category, items in summary_data.items():
        category = category.title()
        categories[category] = []
        for item in items:
            categories[category].append({
                'domain': item['domain'].upper(),
                'summary': item['summary'],
                'title': item['title'].capitalize(),
                'url': item['url']
            })

    # Render the template
    html_content = template.render(categories=categories)

    # Generate filename with current date
    current_date = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    filename = f"{current_date}_summary.html"

    # Ensure the directory exists
    content_folder = os.path.join(data_folder, 'summaries')
    os.makedirs(content_folder, exist_ok=True)

    # Write the HTML file
    with open(os.path.join(content_folder, filename), 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"Generated HTML summary: {filename}")
