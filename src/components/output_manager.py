import json
import os
from pathlib import Path
from datetime import datetime
import sys
from typing import Dict, List
from src.entity.artifacts import OutputManagerArtifact
from src.entity.config_entity import OutputManagerConfig, ConfigEntity
from src.logger import logging
from src.exceptions import CustomException

class OutputManager:
    def __init__(self):
        self.config = OutputManagerConfig(config=ConfigEntity())
        self.setup_output_directory()
        logging.info("OutputManager initialized")

    def setup_output_directory(self):
        """Setup output directory structure"""
        try:
            output_path = Path(self.config.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Output directory ensured: {output_path}")
        except Exception as e:
            logging.error(f"Error creating output directory: {str(e)}")
            raise CustomException(e, sys)

    def save_categorized_news(self, categorized_news: Dict[str, List[Dict]], 
                             total_images: int = 0) -> str:
        """Save categorized news data to JSON file"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
            filename = f"{self.config.news_data_prefix}_{timestamp}{self.config.json_extension}"
            file_path = Path(self.config.output_dir) / filename
            
            total_articles = sum(len(articles) for articles in categorized_news.values())
            
            json_data = {
                'timestamp': datetime.now().isoformat(),
                'total_articles': total_articles,
                'categories': self.config.target_categories,
                'target_per_category': 10,
                'selection_method': 'Top buzz score with guaranteed minimum',
                'total_images': total_images,
                'categorized_news': categorized_news
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            file_size = os.path.getsize(file_path)
            
            logging.info(f"Categorized news saved to: {filename}")
            logging.info(f"Total articles: {total_articles}, File size: {file_size} bytes")
            
            return str(file_path)
            
        except Exception as e:
            logging.error(f"Error saving categorized news: {str(e)}")
            raise CustomException(e, sys)

    def save_processed_memes(self, processed_articles: List[Dict]) -> OutputManagerArtifact:
        """Save processed meme data to JSON file"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
            filename = f"{self.config.processed_memes_prefix}_{timestamp}{self.config.json_extension}"
            file_path = Path(self.config.output_dir) / filename
            
            # Calculate statistics
            templates_found = len([a for a in processed_articles if a.get('template_image_path')])
            
            output_data = {
                'timestamp': datetime.now().isoformat(),
                'total_processed': len(processed_articles),
                'total_api_calls': len(processed_articles),
                'processing_type': 'comprehensive_sarcastic_content',
                'fields_generated': ['description', 'category', 'emotion', 'dialogues', 'hashtags', 'template_path'],
                'statistics': {
                    'articles_processed': len(processed_articles),
                    'templates_matched': templates_found,
                    'template_success_rate': f"{(templates_found/len(processed_articles)*100):.1f}%" if processed_articles else "0%"
                },
                'processed_news': processed_articles
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            file_size = os.path.getsize(file_path)
            
            logging.info(f"Processed memes saved to: {filename}")
            logging.info(f"Articles processed: {len(processed_articles)}, Templates: {templates_found}, File size: {file_size} bytes")
            
            return OutputManagerArtifact(
                output_file_path=str(file_path),
                total_articles_saved=len(processed_articles),
                file_size_bytes=file_size,
                timestamp=timestamp
            )
            
        except Exception as e:
            logging.error(f"Error saving processed memes: {str(e)}")
            raise CustomException(e, sys)

    def create_comprehensive_response(self, categorized_news: Dict, processed_articles: List[Dict], 
                                    news_file_path: str, memes_artifact: OutputManagerArtifact,
                                    pipeline_stats: Dict) -> Dict:
        """Create comprehensive API response"""
        try:
            # Calculate statistics
            total_scraped = sum(len(articles) for articles in categorized_news.values())
            total_images = sum(1 for articles in categorized_news.values() 
                             for article in articles if article.get('image_path'))
            templates_found = len([a for a in processed_articles if a.get('template_image_path')])
            
            # Flatten categorized news for response consistency
            flat_scraped_news = []
            for category, articles in categorized_news.items():
                for article in articles:
                    article_with_category = article.copy()
                    article_with_category['scraped_category'] = category
                    flat_scraped_news.append(article_with_category)
            
            # Get categories from processed articles
            categories_processed = list(set([a.get('category', 'unknown') for a in processed_articles]))
            
            response = {
                "timestamp": datetime.now().isoformat(),
                "status": "complete_pipeline_success",
                
                # Pipeline statistics
                "pipeline_stats": {
                    "scraping": {
                        "total_articles": total_scraped,
                        "categories_scraped": list(categorized_news.keys()),
                        "articles_per_category": {cat: len(articles) for cat, articles in categorized_news.items()},
                        "images_scraped": total_images,
                        "scraping_method": "High-buzz selection, 10 per category"
                    },
                    "processing": {
                        "articles_processed": len(processed_articles),
                        "templates_matched": templates_found,
                        "template_success_rate": f"{(templates_found/len(processed_articles)*100):.1f}%" if processed_articles else "0%",
                        "categories_generated": categories_processed,
                        "gemini_api_calls": pipeline_stats.get('total_api_calls', len(processed_articles)),
                        "processing_method": "Single comprehensive call per article"
                    },
                    "overall_success_rate": f"{(len(processed_articles)/total_scraped*100):.1f}%" if total_scraped > 0 else "0%"
                },
                
                # Output files
                "output_files": {
                    "categorized_news_json": news_file_path,
                    "processed_memes_json": memes_artifact.output_file_path,
                    "images_directory": "./artifacts/images/"
                },
                
                # Categorized scraped news data
                "categorized_scraped_news": {
                    "structure": "Organized by categories",
                    "categories": categorized_news
                },
                
                # Flat scraped news (for compatibility)
                "flat_scraped_news": {
                    "total_articles": len(flat_scraped_news),
                    "articles": flat_scraped_news
                },
                
                # Processed memes data
                "processed_memes_data": {
                    "total_memes": len(processed_articles),
                    "fields_per_meme": ["description", "category", "hashtags", "dialogues", "url", "template_image_path"],
                    "memes": processed_articles
                },
                
                # Sample data
                "samples": {
                    "sample_categorized_news": {
                        category: articles[:1] for category, articles in categorized_news.items() if articles
                    },
                    "sample_processed_meme": processed_articles[0] if processed_articles else None
                },
                
                # System information
                "system_info": {
                    "scraper_version": "Enhanced with categorization and buzz scoring",
                    "processor_version": "Gemini 2.0 Flash Lite with comprehensive sarcasm",
                    "emotion_matching": "Smart Supabase template matching",
                    "target_categories": self.config.target_categories,
                    "processing_features": [
                        "Sarcastic descriptions",
                        "Emotion detection",
                        "Category classification", 
                        "Meme dialogues generation",
                        "Viral hashtags creation",
                        "Template matching"
                    ]
                }
            }
            
            return response
            
        except Exception as e:
            logging.error(f"Error creating comprehensive response: {str(e)}")
            raise CustomException(e, sys)
