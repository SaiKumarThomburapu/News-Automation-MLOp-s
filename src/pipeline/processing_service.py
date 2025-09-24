from typing import Dict, List
from supabase import Client
import sys
from src.components.gemini_processor import GeminiProcessor
from src.components.template_manager import TemplateManager
from src.components.output_manager import OutputManager
from src.logger import logging
from src.exceptions import CustomException

class ProcessingService:
    """Service layer for AI processing operations"""
    
    def __init__(self, gemini_api_keys: List[str], supabase_client: Client):
        self.gemini_processor = GeminiProcessor(gemini_api_keys)
        self.template_manager = TemplateManager(supabase_client)
        self.output_manager = OutputManager()
        logging.info("ProcessingService initialized")

    def process_with_ai(self, categorized_news: Dict[str, List[Dict]]) -> Dict:
        """Process articles with AI and match templates"""
        try:
            # Get available emotions
            emotions_list = self.template_manager.get_available_emotions()
            
            # Process with Gemini AI
            logging.info("Processing with Gemini AI...")
            gemini_artifact = self.gemini_processor.process_articles(categorized_news, emotions_list)
            
            if not gemini_artifact.processed_content:
                raise CustomException("No articles processed by Gemini AI", sys)
            
            # Match templates
            logging.info("Matching templates...")
            template_artifact = self.template_manager.match_templates_for_articles(gemini_artifact.processed_content)
            
            # Save processed memes
            logging.info("Saving processed memes...")
            memes_artifact = self.output_manager.save_processed_memes(gemini_artifact.processed_content)
            
            return {
                'processed_articles': gemini_artifact.processed_content,
                'total_api_calls': gemini_artifact.total_api_calls,
                'success_rate': gemini_artifact.success_rate,
                'templates_matched': len(template_artifact.matched_templates),
                'template_success_rate': template_artifact.template_success_rate,
                'output_file_path': memes_artifact.output_file_path,
                'failed_articles': gemini_artifact.failed_articles
            }
            
        except Exception as e:
            logging.error(f"Error in process_with_ai: {str(e)}")
            raise CustomException(e, sys)
