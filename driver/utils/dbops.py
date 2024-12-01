import logging
import sqlite3
import atexit
from datetime import datetime

logger = logging.getLogger(__name__)

# Global connection object
conn = None

def initialize_db(database_file):
    global conn
    conn = sqlite3.connect(database_file)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    atexit.register(close_db)

def close_db():
    global conn
    if conn:
        conn.close()
        conn = None

def get_cursor():
    global conn
    if not conn:
        raise RuntimeError("Database connection not initialized. Call initialize_db() before using database operations.")
    return conn.cursor()

def get_existing_urls_for_domain(domain):
    """
    Retrieve all URLs for a given domain from the SQLite database.
    If the posts table doesn't exist, return an empty list.

    Args:
        domain (str): The domain to fetch URLs for.

    Returns:
        list: A list of URLs associated with the given domain.
    """
    cursor = get_cursor()

    try:
        # Check if the posts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
        if cursor.fetchone() is None:
            logger.debug("Posts table does not exist yet. Returning empty url list for {domain}.")
            return []

        cursor.execute("SELECT url FROM posts WHERE domain = ?", (domain,))
        urls = [row[0] for row in cursor.fetchall()]
        return urls
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return []
    

def get_recent_unprocessed_posts_by_domain(limit=3):
    """
    Retrieve the most recent unprocessed posts for each domain, limited to a specified number per domain.

    Args:
        limit (int): The maximum number of posts to retrieve per domain. Defaults to 3.

    Returns:
        list: A list of dictionaries containing the most recent unprocessed post data for each domain.
    """
    cursor = get_cursor()

    try:
        cursor.execute("""
            WITH ranked_posts AS (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY domain ORDER BY date DESC) as rank
                FROM posts
                WHERE processed = FALSE
            )
            SELECT * FROM ranked_posts
            WHERE rank <= ?
            ORDER BY domain, date DESC
        """, (limit,))
        
        recent_unprocessed_posts = [dict(row) for row in cursor.fetchall()]
        return recent_unprocessed_posts
    except sqlite3.Error as e:
        logger.error(f"Database error when fetching recent unprocessed posts by domain: {e}")
        return []


def get_unprocessed_posts():
    """
    Retrieve all posts from the SQLite database where processed is False.

    Returns:
        list: A list of dictionaries containing unprocessed post data.
    """
    cursor = get_cursor()

    try:
        cursor.execute("""
            SELECT * FROM posts 
            WHERE processed = FALSE
        """)
        
        unprocessed_posts = [dict(row) for row in cursor.fetchall()]
        return unprocessed_posts
    except sqlite3.Error as e:
        logger.error(f"Database error when fetching unprocessed posts: {e}")
        return []


def mark_posts_as_processed(urls):
    """
    Update the 'processed' column to True for the given URLs in the database.

    Args:
        urls (list): A list of URLs to mark as processed.

    Returns:
        int: The number of posts successfully marked as processed.
    """
    cursor = get_cursor()

    try:
        batch_size = 10
        total_rows_affected = 0

        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            
            # Prepare the update query for this batch
            query = '''
                UPDATE posts
                SET processed = TRUE
                WHERE url IN ({})
            '''.format(','.join(['?'] * len(batch)))

            # Execute the update for this batch
            cursor.execute(query, batch)
            conn.commit()

            # Add the number of rows affected in this batch
            total_rows_affected += cursor.rowcount

        logger.info(f"Marked {total_rows_affected} posts as processed.")
        return total_rows_affected
    except sqlite3.Error as e:
        logger.error(f"Database error when marking posts as processed: {e}")
        return 0


def save_summary_to_db(summary):
    cursor = get_cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            subtitle TEXT,
            domain TEXT,
            date TEXT,
            summary TEXT,
            category TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Prepare the insert/update query
    query = '''
        INSERT OR REPLACE INTO summaries
        (url, title, subtitle, domain, date, summary, category)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    '''

    try:
        cursor.execute(query, (
            summary.get('url', ''),
            summary.get('title', ''),
            summary.get('subtitle', ''),
            summary.get('domain', ''),
            summary.get('date', ''),
            summary.get('summary', ''),
            summary.get('category', '')
        ))
        conn.commit()
        logger.info(f"Saved/updated summary for URL: {summary.get('url')}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error when saving summary: {e}")
        return False
    


def save_posts_to_db(posts_data):
    cursor = get_cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT,
            blog_title TEXT,
            url TEXT UNIQUE,
            title TEXT,
            subtitle TEXT,
            like_count INTEGER,
            date TEXT,
            md TEXT,
            source TEXT,
            created_at TEXT,
            updated_at TEXT,
            processed BOOLEAN DEFAULT FALSE
        )
    ''')

    # Prepare the insert/update query
    query = '''
        INSERT OR REPLACE INTO posts 
        (domain, blog_title, url, title, subtitle, like_count, date, md, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM posts WHERE url = ?), ?), ?)
    '''

    current_time = datetime.now().isoformat()

    # Insert or update each post
    for post in posts_data:
        cursor.execute(query, (
            post.get('domain', ''),
            post.get('blog_title', ''),
            post.get('url', ''),
            post.get('title', ''),
            post.get('subtitle', ''),
            post.get('like_count', 0),
            post.get('date', ''),
            post.get('md', ''),
            'Substack',  # Source is set to 'Substack' for this scraper
            post.get('url', ''),  # For checking if the post already exists
            current_time,  # created_at (only used for new posts)
            current_time   # updated_at
        ))

    conn.commit()

    logger.info(f"Saved {len(posts_data)} posts to the database.")
