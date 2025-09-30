import sys
from datetime import datetime
from typing import Dict, List
from supabase import Client

from src.components.news_extractor import NewsExtractor
from src.components.content_processor import ContentProcessor
from src.components.image_downloader import ImageDownloader
from src.components.gemini_processor import GeminiProcessor
from src.components.template_manager import TemplateManager
from src.components.output_manager import OutputManager
from src.components.meme_generator import MemeGenerator
from src.logger import logging
from src.exceptions import CustomException

def scrape_and_process_news() -> Dict:
    """Scrape news and process content with images"""
    try:
        # Initialize components for this function
        news_extractor = NewsExtractor()
        content_processor = ContentProcessor()
        image_downloader = ImageDownloader()
        
        # Extract news from all sources
        logging.info("Starting news extraction...")
        news_artifact = news_extractor.extract_all_sources()
        
        if not news_artifact.scraped_articles:
            raise CustomException("No articles extracted from sources", sys)
        
        # Process and categorize content
        logging.info("Processing content...")
        content_artifact = content_processor.process_articles(news_artifact.scraped_articles)
        
        if not content_artifact.processed_articles:
            raise CustomException("No articles after content processing", sys)
        
        # Download images
        logging.info("Downloading images...")
        image_artifact = image_downloader.download_images_for_articles(content_artifact.categorized_news)
        
        return {
            'categorized_news': content_artifact.categorized_news,
            'total_articles': sum(len(articles) for articles in content_artifact.categorized_news.values()),
            'total_images': len(image_artifact.downloaded_images),
            'sources_scraped': news_artifact.sources_scraped,
            'unique_articles_count': content_artifact.unique_articles_count,
            'image_artifact': image_artifact
        }
        
    except Exception as e:
        logging.error(f"Error in scrape_and_process_news: {str(e)}")
        raise CustomException(e, sys)

def process_with_ai(categorized_news: Dict[str, List[Dict]], gemini_api_keys: List[str], supabase_client: Client) -> Dict:
    """Process articles with AI and match templates"""
    try:
        # Initialize components for this function
        gemini_processor = GeminiProcessor(gemini_api_keys)
        template_manager = TemplateManager(supabase_client)
        output_manager = OutputManager()
        meme_generator = MemeGenerator()
        
        # Get available emotions
        emotions_list = template_manager.get_available_emotions()
        
        # Process with Gemini AI
        logging.info("Processing with Gemini AI...")
        gemini_artifact = gemini_processor.process_articles(categorized_news, emotions_list)
        
        if not gemini_artifact.processed_content:
            raise CustomException("No articles processed by Gemini AI", sys)
        
        # Match templates
        logging.info("Matching templates...")
        template_artifact = template_manager.match_templates_for_articles(gemini_artifact.processed_content)
        
        # Generate memes with overlaid dialogues
        logging.info("Generating memes with overlaid dialogues...")
        memes_generated = 0
        memes_failed = 0
        
        for article in gemini_artifact.processed_content:
            try:
                if article.get('template_base64') and article.get('dialogues'):
                    overlaid_meme = meme_generator.generate_meme_with_overlay(
                        article['template_base64'], 
                        article['dialogues']
                    )
                    article['final_meme_base64'] = overlaid_meme
                    memes_generated += 1
                else:
                    article['final_meme_base64'] = None
                    memes_failed += 1
            except Exception as e:
                logging.error(f"Error generating meme for article: {str(e)}")
                article['final_meme_base64'] = None
                memes_failed += 1
        
        # Get meme generation statistics
        meme_stats = meme_generator.get_generation_statistics()
        
        # Save processed memes
        logging.info("Saving processed memes...")
        memes_artifact = output_manager.save_clean_processed_memes(gemini_artifact.processed_content)
        
        return {
            'processed_articles': gemini_artifact.processed_content,
            'total_api_calls': gemini_artifact.total_api_calls,
            'success_rate': gemini_artifact.success_rate,
            'templates_matched': len(template_artifact.matched_templates),
            'template_success_rate': template_artifact.template_success_rate,
            'memes_generated': memes_generated,
            'memes_failed': memes_failed,
            'meme_generation_success_rate': (memes_generated / (memes_generated + memes_failed) * 100) if (memes_generated + memes_failed) > 0 else 0.0,
            'output_file_path': memes_artifact.output_file_path,
            'failed_articles': gemini_artifact.failed_articles,
            'template_artifact': template_artifact,
            'memes_artifact': memes_artifact,
            'meme_stats': meme_stats
        }
        
    except Exception as e:
        logging.error(f"Error in process_with_ai: {str(e)}")
        raise CustomException(e, sys)

def execute_complete_pipeline(gemini_api_keys: List[str], supabase_client: Client) -> Dict:
    """Execute the complete news meme generation pipeline"""
    try:
        logging.info("="*80)
        logging.info("Starting COMPLETE NEWS MEME PIPELINE")
        logging.info("="*80)
        
        # Step 1-3: Scraping and initial processing
        logging.info("PHASE 1: Scraping and Processing News...")
        scraping_results = scrape_and_process_news()
        
        # Step 4: Save clean categorized news
        logging.info("STEP 4: Saving clean categorized news...")
        output_manager = OutputManager()
        news_file_path = output_manager.save_clean_categorized_news(scraping_results['categorized_news'])
        
        # Step 5-7: AI processing and template matching
        logging.info("PHASE 2: AI Processing and Template Matching...")
        ai_results = process_with_ai(scraping_results['categorized_news'], gemini_api_keys, supabase_client)
        
        # Step 8: Save clean processed memes (already done in process_with_ai)
        logging.info("STEP 8: Processed memes already saved with base64 templates and final memes")
        
        # Step 9: Create comprehensive response
        logging.info("STEP 9: Creating final response...")
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "pipeline_stats": {
                "articles_scraped": scraping_results['total_articles'],
                "articles_processed": len(ai_results['processed_articles']),
                "images_downloaded": scraping_results['total_images'],
                "templates_matched": ai_results['templates_matched'],
                "final_memes_generated": ai_results['memes_generated'],
                "success_rate": f"{ai_results['success_rate']:.1f}%",
                "template_success_rate": f"{ai_results['template_success_rate']:.1f}%",
                "meme_generation_success_rate": f"{ai_results['meme_generation_success_rate']:.1f}%"
            },
            "output_files": {
                "news_data": news_file_path,
                "processed_memes": ai_results['output_file_path'],
                "images_directory": scraping_results['image_artifact'].images_directory
            },
            "detailed_results": {
                "sources_scraped": scraping_results['sources_scraped'],
                "unique_articles": scraping_results['unique_articles_count'],
                "total_api_calls": ai_results['total_api_calls'],
                "failed_articles": len(ai_results['failed_articles']),
                "memes_failed": ai_results['memes_failed']
            },
            "message": f"Pipeline completed successfully! Generated {ai_results['memes_generated']} final memes from {ai_results['templates_matched']} templates and {scraping_results['total_images']} images."
        }
        
        logging.info("="*80)
        logging.info("UNIFIED PIPELINE COMPLETED SUCCESSFULLY!")
        logging.info(f"Final Results:")
        logging.info(f"  - Articles scraped: {scraping_results['total_articles']}")
        logging.info(f"  - Articles processed: {len(ai_results['processed_articles'])}")
        logging.info(f"  - Images downloaded: {scraping_results['total_images']}")
        logging.info(f"  - Templates matched: {ai_results['templates_matched']}")
        logging.info(f"  - Final memes generated: {ai_results['memes_generated']}")
        logging.info(f"  - Success rate: {ai_results['success_rate']:.1f}%")
        logging.info("="*80)
        
        return response
        
    except Exception as e:
        logging.error(f"Unified pipeline execution failed: {str(e)}")
        raise CustomException(e, sys)

def execute_scraping_only() -> Dict:
    """Execute only the scraping phase"""
    try:
        logging.info("Executing scraping-only pipeline...")
        results = scrape_and_process_news()
        
        # Save news data
        output_manager = OutputManager()
        news_file_path = output_manager.save_clean_categorized_news(results['categorized_news'])
        results['news_file_path'] = news_file_path
        
        return results
        
    except Exception as e:
        logging.error(f"Scraping-only pipeline failed: {str(e)}")
        raise CustomException(e, sys)

def execute_processing_only(categorized_news: Dict[str, List[Dict]], gemini_api_keys: List[str], supabase_client: Client) -> Dict:
    """Execute only the AI processing phase"""
    try:
        logging.info("Executing processing-only pipeline...")
        results = process_with_ai(categorized_news, gemini_api_keys, supabase_client)
        
        return results
        
    except Exception as e:
        logging.error(f"Processing-only pipeline failed: {str(e)}")
        raise CustomException(e, sys)

 