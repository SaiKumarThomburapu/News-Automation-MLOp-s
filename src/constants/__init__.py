# Constants for News Meme Generation Pipeline

import random

# Directory structure
OUTPUT_DIR = "artifacts"
IMAGES_DIR = "images"
LOGS_DIR = "logs"

# File naming patterns
NEWS_DATA_PREFIX = "news_data"
PROCESSED_MEMES_PREFIX = "sarcastic_news_memes"
JSON_EXTENSION = ".json"
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

# News extraction constants
TARGET_CATEGORIES = ['politics', 'movies', 'entertainment', 'sports', 'business', 'technology']
ARTICLES_PER_CATEGORY = 10
MAX_ARTICLES_PER_SOURCE = 30
MIN_TITLE_LENGTH = 10
MIN_CONTENT_LENGTH = 15

# Scraping configuration
REQUEST_TIMEOUT = 15
SCRAPING_DELAY_MIN = 0.3
SCRAPING_DELAY_MAX = 0.8
MAX_RETRIES = 3

# Headers for web requests
def get_random_user_agent():
    return f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 120)}.0.0.0 Safari/537.36'

DEFAULT_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

# News sources configuration
NEWS_SOURCES = {
    # Politics sources
    'ie_politics': {'url': 'https://indianexpress.com/section/political-pulse/', 'selectors': ['h3 a', 'h2 a'], 'category': 'politics'},
    'toi_politics': {'url': 'https://timesofindia.indiatimes.com/india', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'category': 'politics'},
    'ht_politics': {'url': 'https://www.hindustantimes.com/india-news', 'selectors': ['h3 a', 'h2 a'], 'category': 'politics'},
    
    # Entertainment & movies sources
    'toi_entertainment': {'url': 'https://timesofindia.indiatimes.com/entertainment', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'category': 'entertainment'},
    'toi_movies': {'url': 'https://timesofindia.indiatimes.com/entertainment/bollywood', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'category': 'movies'},
    'news18_entertainment': {'url': 'https://www.news18.com/entertainment/', 'selectors': ['h3 a', 'h2 a'], 'category': 'entertainment'},
    'ie_entertainment': {'url': 'https://indianexpress.com/section/entertainment/', 'selectors': ['h3 a', 'h2 a'], 'category': 'entertainment'},
    
    # Sports sources
    'toi_sports': {'url': 'https://timesofindia.indiatimes.com/sports', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'category': 'sports'},
    'ht_sports': {'url': 'https://www.hindustantimes.com/sports', 'selectors': ['h3 a', 'h2 a'], 'category': 'sports'},
    'ie_sports': {'url': 'https://indianexpress.com/section/sports/', 'selectors': ['h3 a', 'h2 a'], 'category': 'sports'},
    
    # Business sources
    'economic_times': {'url': 'https://economictimes.indiatimes.com/', 'selectors': ['h3 a', 'h2 a'], 'category': 'business'},
    'livemint': {'url': 'https://www.livemint.com/', 'selectors': ['h3 a', 'h2 a'], 'category': 'business'},
    'moneycontrol': {'url': 'https://www.moneycontrol.com/news/', 'selectors': ['h3 a', 'h2 a'], 'category': 'business'},
    
    # Technology sources
    'toi_technology': {'url': 'https://timesofindia.indiatimes.com/gadgets-news', 'selectors': ['a[href*="/articleshow/"]', 'h3 a'], 'category': 'technology'},
    'et_tech': {'url': 'https://economictimes.indiatimes.com/tech', 'selectors': ['h3 a', 'h2 a'], 'category': 'technology'},
    'ht_tech': {'url': 'https://www.hindustantimes.com/tech', 'selectors': ['h3 a', 'h2 a'], 'category': 'technology'},
}

# Buzz score keywords
HIGH_BUZZ_WORDS = {
    'breaking': 4, 'exclusive': 3, 'shocking': 3, 'controversy': 3,
    'scandal': 3, 'arrest': 2, 'murder': 3, 'viral': 3,
    'trending': 2, 'major': 2, 'important': 2, 'crisis': 2,
    'emergency': 2, 'urgent': 2, 'alert': 2, 'warning': 1,
    'wins': 2, 'loses': 1, 'victory': 2, 'defeat': 1, 'new': 1
}

CATEGORY_BUZZ_WORDS = {
    'bollywood': 2, 'cricket': 2, 'election': 2, 'politics': 1,
    'technology': 1, 'business': 1, 'sports': 1, 'movie': 1,
    'celebrity': 1, 'actor': 1, 'match': 1, 'win': 1, 'lose': 1,
    'ipl': 2, 'box office': 2, 'release': 1, 'hit': 1, 'flop': 1,
    'update': 1, 'news': 1, 'latest': 1, 'today': 1
}

# Category classification keywords
CATEGORY_KEYWORDS = {
    'politics': ['election', 'parliament', 'minister', 'government', 'political', 'bjp', 'congress', 'modi', 'politics', 'vote', 'party', 'constituency', 'leader', 'pm', 'chief minister'],
    'movies': ['movie', 'film', 'actor', 'actress', 'bollywood', 'cinema', 'box office', 'trailer', 'director', 'producer', 'release', 'star', 'role', 'shoot', 'debut'],
    'entertainment': ['entertainment', 'celebrity', 'music', 'tv show', 'award', 'concert', 'performance', 'artist', 'singer', 'album', 'show', 'reality', 'dance', 'talent'],
    'sports': ['cricket', 'football', 'sports', 'match', 'player', 'ipl', 'olympics', 'tournament', 'team', 'game', 'score', 'win', 'lose', 'champion', 'league'],
    'business': ['business', 'market', 'stock', 'economy', 'startup', 'investment', 'ipo', 'company', 'profit', 'revenue', 'financial', 'bank', 'money', 'price', 'growth'],
    'technology': ['technology', 'tech', 'ai', 'software', 'app', 'smartphone', 'digital', 'internet', 'gadget', 'innovation', 'cyber', 'data', 'android', 'apple', 'google']
}

# Image processing constants
MIN_IMAGE_SIZE_BYTES = 1000
VALID_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']
SKIP_IMAGE_PATTERNS = ['logo', 'icon', 'avatar', 'placeholder', '1x1', 'pixel', 'spacer']

# Gemini API configuration
GEMINI_MODEL_NAME = 'gemini-2.0-flash-lite'
MAX_CALLS_PER_KEY_PER_MINUTE = 10
API_CALL_DELAY = 3
GEMINI_REQUEST_TIMEOUT = 30
MAX_GEMINI_RETRIES = 3

# Buzz score configuration
BASE_BUZZ_SCORE = 1
MAX_BUZZ_SCORE = 15
CONTENT_LENGTH_BONUS_THRESHOLD_1 = 50
CONTENT_LENGTH_BONUS_THRESHOLD_2 = 150
TITLE_LENGTH_BONUS_THRESHOLD = 30

# Supabase configuration
SUPABASE_SCHEMA = 'dc'
EMOTIONS_TABLE = 'emotions'
MEMES_TABLE = 'memes_dc'
SIMILARITY_THRESHOLD = 0.5

# Content processing thresholds
DUPLICATE_CONTENT_HASH_LENGTH = 32
MAX_CONTENT_PARTS = 3
MAX_CONTENT_LENGTH = 800
