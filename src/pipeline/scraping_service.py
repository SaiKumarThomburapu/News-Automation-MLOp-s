from typing import Dict, List
import sys
from src.components.news_extractor import NewsExtractor
from src.components.content_processor import ContentProcessor
from src.components.image_downloader import ImageDownloader
from src.logger import logging
from src.exceptions import CustomException

class ScrapingService:
    """Service layer for news scraping operations"""
    
    def __init__(self):
        self.news_extractor = NewsExtractor()
        self.content_processor = ContentProcessor()
        self.image_downloader = ImageDownloader()
        logging.info("ScrapingService initialized")

    def scrape_and_process_news(self) -> Dict:
        """Scrape news and process content with images"""
        try:
            # Extract news from all sources
            logging.info("Starting news extraction...")
            news_artifact = self.news_extractor.extract_all_sources()
            
            if not news_artifact.scraped_articles:
                raise CustomException("No articles extracted from sources", sys)
            
            # Process and categorize content
            logging.info("Processing content...")
            content_artifact = self.content_processor.process_articles(news_artifact.scraped_articles)
            
            if not content_artifact.processed_articles:
                raise CustomException("No articles after content processing", sys)
            
            # Download images
            logging.info("Downloading images...")
            image_artifact = self.image_downloader.download_images_for_articles(content_artifact.categorized_news)
            
            return {
                'categorized_news': content_artifact.categorized_news,
                'total_articles': sum(len(articles) for articles in content_artifact.categorized_news.values()),
                'total_images': len(image_artifact.downloaded_images),
                'sources_scraped': news_artifact.sources_scraped,
                'unique_articles_count': content_artifact.unique_articles_count
            }
            
        except Exception as e:
            logging.error(f"Error in scrape_and_process_news: {str(e)}")
            raise CustomException(e, sys)
