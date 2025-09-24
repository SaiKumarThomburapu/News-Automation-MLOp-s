import sys
from typing import Dict, List
from src.components.news_extractor import NewsExtractor
from src.components.content_processor import ContentProcessor
from src.components.image_downloader import ImageDownloader
from src.components.gemini_processor import GeminiProcessor
from src.components.template_manager import TemplateManager
from src.components.output_manager import OutputManager
from src.logger import logging
from src.exceptions import CustomException

class NewsPipeline:
    def __init__(self, gemini_api_keys: List[str], supabase_client):
        """Initialize the complete news meme generation pipeline"""
        self.news_extractor = NewsExtractor()
        self.content_processor = ContentProcessor()
        self.image_downloader = ImageDownloader()
        self.gemini_processor = GeminiProcessor(gemini_api_keys)
        self.template_manager = TemplateManager(supabase_client)
        self.output_manager = OutputManager()
        
        logging.info("NewsPipeline initialized with all components")

    def execute_complete_pipeline(self) -> Dict:
        """Execute the complete news meme generation pipeline"""
        try:
            logging.info("="*80)
            logging.info("Starting COMPLETE NEWS MEME PIPELINE")
            logging.info("="*80)
            
            # Step 1: Extract news from all sources
            logging.info("STEP 1: Extracting news from all sources...")
            news_artifact = self.news_extractor.extract_all_sources()
            
            if not news_artifact.scraped_articles:
                raise CustomException("No articles were extracted from any source", sys)
            
            logging.info(f"News extraction completed: {news_artifact.total_articles} articles from {len(news_artifact.sources_scraped)} sources")
            
            # Step 2: Process and categorize content
            logging.info("STEP 2: Processing and categorizing content...")
            content_artifact = self.content_processor.process_articles(news_artifact.scraped_articles)
            
            if not content_artifact.processed_articles:
                raise CustomException("No articles remained after content processing", sys)
            
            total_categorized = sum(len(articles) for articles in content_artifact.categorized_news.values())
            logging.info(f"Content processing completed: {total_categorized} articles categorized")
            
            # Step 3: Download images for articles
            logging.info("STEP 3: Downloading images for articles...")
            image_artifact = self.image_downloader.download_images_for_articles(content_artifact.categorized_news)
            
            logging.info(f"Image downloading completed: {len(image_artifact.downloaded_images)} images downloaded")
            
            # Step 4: Save categorized news
            logging.info("STEP 4: Saving categorized news...")
            news_file_path = self.output_manager.save_categorized_news(
                content_artifact.categorized_news,
                len(image_artifact.downloaded_images)
            )
            
            # Step 5: Process with Gemini AI
            logging.info("STEP 5: Processing articles with Gemini AI...")
            emotions_list = self.template_manager.get_available_emotions()
            gemini_artifact = self.gemini_processor.process_articles(
                content_artifact.categorized_news, 
                emotions_list
            )
            
            if not gemini_artifact.processed_content:
                raise CustomException("No articles were successfully processed by Gemini AI", sys)
            
            logging.info(f"Gemini processing completed: {len(gemini_artifact.processed_content)} articles processed ({gemini_artifact.success_rate:.1f}%)")
            
            # Step 6: Match templates
            logging.info("STEP 6: Matching emotion-based templates...")
            template_artifact = self.template_manager.match_templates_for_articles(gemini_artifact.processed_content)
            
            logging.info(f"Template matching completed: {len(template_artifact.matched_templates)} templates matched ({template_artifact.template_success_rate:.1f}%)")
            
            # Step 7: Save processed memes
            logging.info("STEP 7: Saving processed memes...")
            memes_artifact = self.output_manager.save_processed_memes(gemini_artifact.processed_content)
            
            # Step 8: Create comprehensive response
            logging.info("STEP 8: Creating comprehensive response...")
            pipeline_stats = {
                'total_api_calls': gemini_artifact.total_api_calls,
                'sources_scraped': len(news_artifact.sources_scraped),
                'images_downloaded': len(image_artifact.downloaded_images),
                'templates_matched': len(template_artifact.matched_templates)
            }
            
            response = self.output_manager.create_comprehensive_response(
                content_artifact.categorized_news,
                gemini_artifact.processed_content,
                news_file_path,
                memes_artifact,
                pipeline_stats
            )
            
            logging.info("="*80)
            logging.info("PIPELINE COMPLETED SUCCESSFULLY!")
            logging.info(f"Final Results:")
            logging.info(f"  - Articles scraped: {news_artifact.total_articles}")
            logging.info(f"  - Articles processed: {len(gemini_artifact.processed_content)}")
            logging.info(f"  - Images downloaded: {len(image_artifact.downloaded_images)}")
            logging.info(f"  - Templates matched: {len(template_artifact.matched_templates)}")
            logging.info(f"  - Success rate: {gemini_artifact.success_rate:.1f}%")
            logging.info("="*80)
            
            return response
            
        except Exception as e:
            logging.error(f"Pipeline execution failed: {str(e)}")
            raise CustomException(e, sys)
