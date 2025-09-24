import os
from pathlib import Path
from bs4 import BeautifulSoup
import sys
from typing import List, Dict, Set
from src.entity.artifacts import ImageDownloaderArtifact
from src.entity.config_entity import ImageDownloaderConfig, ConfigEntity
from src.logger import logging
from src.exceptions import CustomException
from src.utils.image_utils import is_valid_image_url, normalize_image_url, get_image_url_from_element, download_image_with_validation
from src.constants import get_random_user_agent

class ImageDownloader:
    def __init__(self):
        self.config = ImageDownloaderConfig(config=ConfigEntity())
        self.downloaded_hashes: Set[str] = set()
        self.setup_images_directory()
        logging.info("ImageDownloader initialized")

    def setup_images_directory(self):
        """Setup images directory structure"""
        try:
            images_path = Path(self.config.output_dir) / self.config.images_dir
            images_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Images directory created: {images_path}")
        except Exception as e:
            logging.error(f"Error creating images directory: {str(e)}")
            raise CustomException(e, sys)

    def extract_image_from_article(self, article: Dict) -> str:
        """Extract image URL from article content or source"""
        try:
            # Try to extract from the article's listing content
            if 'listing_element' in article:
                return self.extract_image_from_listing(article['listing_element'], article['url'])
            
            # If no listing element, try to find images in the content
            return None
            
        except Exception as e:
            logging.warning(f"Error extracting image from article: {str(e)}")
            return None

    def extract_image_from_listing(self, link_element, base_url: str) -> str:
        """Extract image from article listing element"""
        try:
            # Look for images in the headline container
            headline_container = link_element.parent
            if headline_container:
                container_images = headline_container.select('img')
                for img in container_images:
                    img_url = get_image_url_from_element(img)
                    if img_url and is_valid_image_url(img_url, self.config.skip_image_patterns):
                        normalized_url = normalize_image_url(img_url, base_url)
                        if normalized_url:
                            return normalized_url
            
            # Look in parent container if not found
            if headline_container and headline_container.parent:
                parent_images = headline_container.parent.select('img')
                for img in parent_images:
                    img_url = get_image_url_from_element(img)
                    if img_url and is_valid_image_url(img_url, self.config.skip_image_patterns):
                        normalized_url = normalize_image_url(img_url, base_url)
                        if normalized_url:
                            return normalized_url
            
            return None
            
        except Exception as e:
            logging.warning(f"Error extracting image from listing: {str(e)}")
            return None

    def download_article_image(self, article: Dict, index: int) -> str:
        """Download image for a specific article"""
        try:
            image_url = self.extract_image_from_article(article)
            if not image_url:
                return None
            
            # Create filename
            category = article.get('final_category', article.get('category', 'general'))
            source = article.get('source', 'unknown')
            filename = f"{category}_{source}_{index}"
            
            # Create full path without extension (will be added by download function)
            images_dir = Path(self.config.output_dir) / self.config.images_dir
            output_path = images_dir / filename
            
            # Update headers with random user agent
            headers = self.config.default_headers.copy()
            headers['User-Agent'] = get_random_user_agent()
            
            # Download image with validation
            downloaded_path = download_image_with_validation(
                image_url,
                str(output_path),
                headers,
                self.config.min_image_size_bytes,
                self.downloaded_hashes
            )
            
            if downloaded_path:
                logging.info(f"Image downloaded: {os.path.basename(downloaded_path)}")
                return downloaded_path
            else:
                logging.warning(f"Failed to download image: {image_url}")
                return None
                
        except Exception as e:
            logging.error(f"Error downloading image for article {index}: {str(e)}")
            return None

    def download_images_for_articles(self, categorized_articles: Dict[str, List[Dict]]) -> ImageDownloaderArtifact:
        """Download images for all articles in categorized structure"""
        try:
            downloaded_images = []
            failed_downloads = []
            total_processed = 0
            
            for category, articles in categorized_articles.items():
                logging.info(f"Processing images for {category} category ({len(articles)} articles)")
                
                for i, article in enumerate(articles):
                    total_processed += 1
                    
                    downloaded_path = self.download_article_image(article, i)
                    
                    if downloaded_path:
                        downloaded_images.append(downloaded_path)
                        # Add image path to article
                        article['image_path'] = downloaded_path
                    else:
                        failed_downloads.append(article.get('url', f"{category}_{i}"))
                        # Set image path to None
                        article['image_path'] = None
            
            images_dir = str(Path(self.config.output_dir) / self.config.images_dir)
            
            logging.info(f"Image download completed: {len(downloaded_images)} successful, {len(failed_downloads)} failed")
            
            return ImageDownloaderArtifact(
                downloaded_images=downloaded_images,
                failed_downloads=failed_downloads,
                total_images_processed=total_processed,
                images_directory=images_dir
            )
            
        except Exception as e:
            logging.error(f"Error in download_images_for_articles: {str(e)}")
            raise CustomException(e, sys)
