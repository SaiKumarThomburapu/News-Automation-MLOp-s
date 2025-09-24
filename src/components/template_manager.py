from supabase import Client
import random
import sys
from typing import Dict, List, Optional
from src.entity.artifacts import TemplateManagerArtifact
from src.entity.config_entity import TemplateManagerConfig, ConfigEntity
from src.logger import logging
from src.exceptions import CustomException
from src.utils.supabase_utils import load_emotions_from_database, get_template_by_emotion_id, get_random_template
from src.utils.text_utils import find_most_similar_text

class TemplateManager:
    def __init__(self, supabase_client: Client):
        self.config = TemplateManagerConfig(config=ConfigEntity())
        self.supabase_client = supabase_client
        
        # Try different table name formats
        possible_emotions_tables = [
            self.config.emotions_table,  # Just 'emotions'
            f"{self.config.supabase_schema}.{self.config.emotions_table}",  # 'dc.emotions'
        ]
        
        self.emotions_db = {}
        
        # Try each table format until one works
        for table_name in possible_emotions_tables:
            logging.info(f"Trying to load emotions from: {table_name}")
            self.emotions_db = load_emotions_from_database(
                supabase_client, 
                self.config.supabase_schema, 
                table_name
            )
            if self.emotions_db:
                self.emotions_table_name = table_name
                logging.info(f"Successfully loaded emotions using table: {table_name}")
                break
        
        if not self.emotions_db:
            logging.warning("Could not load emotions from any table format. Template matching will be limited.")
            self.emotions_table_name = self.config.emotions_table
        
        # Set memes table name
        self.memes_table_name = self.config.memes_table
        
        logging.info(f"TemplateManager initialized with {len(self.emotions_db)} emotions")

    def find_template_by_emotion(self, detected_emotion: str) -> Optional[str]:
        """Find meme template by emotion with smart matching"""
        try:
            detected_emotion_lower = detected_emotion.lower().strip()
            
            if not self.emotions_db:
                logging.warning("No emotions loaded, cannot match templates")
                return None
            
            # First, try exact match
            if detected_emotion_lower in self.emotions_db:
                emotion_id = self.emotions_db[detected_emotion_lower]['emotion_id']
                template_path = get_template_by_emotion_id(
                    self.supabase_client,
                    self.config.supabase_schema,
                    self.memes_table_name,
                    emotion_id
                )
                if template_path:
                    logging.info(f"Found exact emotion match: {detected_emotion_lower}")
                    return template_path
            
            # If exact match fails, find nearest emotion
            available_emotions = list(self.emotions_db.keys())
            nearest_emotion = find_most_similar_text(
                detected_emotion_lower, 
                available_emotions, 
                self.config.similarity_threshold
            )
            
            if nearest_emotion and nearest_emotion != detected_emotion_lower:
                emotion_id = self.emotions_db[nearest_emotion]['emotion_id']
                template_path = get_template_by_emotion_id(
                    self.supabase_client,
                    self.config.supabase_schema,
                    self.memes_table_name,
                    emotion_id
                )
                if template_path:
                    logging.info(f"Found similar emotion match: {detected_emotion_lower} -> {nearest_emotion}")
                    return template_path
            
            # If still no match, get random template
            template_path = get_random_template(
                self.supabase_client,
                self.config.supabase_schema,
                self.memes_table_name
            )
            if template_path:
                logging.info(f"Used random template for emotion: {detected_emotion_lower}")
                return template_path
            
            return None
            
        except Exception as e:
            logging.error(f"Error finding template for emotion '{detected_emotion}': {str(e)}")
            return None

    def match_templates_for_articles(self, processed_articles: List[Dict]) -> TemplateManagerArtifact:
        """Match templates for all processed articles"""
        try:
            matched_templates = []
            unmatched_emotions = []
            emotions_matched = []
            
            for i, article in enumerate(processed_articles):
                detected_emotion = article.get('emotion', '')
                
                if detected_emotion and self.emotions_db:
                    template_path = self.find_template_by_emotion(detected_emotion)
                    
                    if template_path:
                        matched_templates.append(template_path)
                        emotions_matched.append(detected_emotion)
                        # Add template path to article
                        article['template_image_path'] = template_path
                        logging.info(f"Template matched for article {i+1}: {detected_emotion}")
                    else:
                        unmatched_emotions.append(detected_emotion)
                        article['template_image_path'] = None
                        logging.warning(f"No template found for article {i+1}: {detected_emotion}")
                else:
                    unmatched_emotions.append("no_emotion" if not detected_emotion else "no_emotions_db")
                    article['template_image_path'] = None
                    logging.warning(f"No emotion or emotions DB for article {i+1}")
            
            template_success_rate = (len(matched_templates) / len(processed_articles)) * 100 if processed_articles else 0
            
            logging.info(f"Template matching completed: {len(matched_templates)}/{len(processed_articles)} templates matched ({template_success_rate:.1f}%)")
            
            return TemplateManagerArtifact(
                matched_templates=matched_templates,
                template_success_rate=template_success_rate,
                emotions_matched=emotions_matched,
                unmatched_emotions=unmatched_emotions
            )
            
        except Exception as e:
            logging.error(f"Error in match_templates_for_articles: {str(e)}")
            raise CustomException(e, sys)

    def get_available_emotions(self) -> List[str]:
        """Get list of available emotions from database"""
        if self.emotions_db:
            return list(self.emotions_db.keys())
        else:
            # Return some default emotions if database isn't available
            logging.warning("No emotions database available, returning default emotions")
            return ['happy', 'sad', 'angry', 'surprised', 'disgusted', 'fearful', 'sarcasm']










# from supabase import Client
# import random
# import sys
# from typing import Dict, List, Optional
# from src.entity.artifacts import TemplateManagerArtifact
# from src.entity.config_entity import TemplateManagerConfig, ConfigEntity
# from src.logger import logging
# from src.exceptions import CustomException
# from src.utils.supabase_utils import load_emotions_from_database, get_template_by_emotion_id, get_random_template
# from src.utils.text_utils import find_most_similar_text

# class TemplateManager:
#     def __init__(self, supabase_client: Client):
#         self.config = TemplateManagerConfig(config=ConfigEntity())
#         self.supabase_client = supabase_client
        
#         # Load emotions from database - use schema.table format
#         emotions_table = f"{self.config.supabase_schema}.{self.config.emotions_table}"
#         self.emotions_db = load_emotions_from_database(
#             supabase_client, 
#             self.config.supabase_schema, 
#             emotions_table
#         )
        
#         logging.info(f"TemplateManager initialized with {len(self.emotions_db)} emotions")

#     def find_template_by_emotion(self, detected_emotion: str) -> Optional[str]:
#         """Find meme template by emotion with smart matching"""
#         try:
#             detected_emotion_lower = detected_emotion.lower().strip()
            
#             # Use schema.table format for memes table
#             memes_table = f"{self.config.supabase_schema}.{self.config.memes_table}"
            
#             # First, try exact match
#             if detected_emotion_lower in self.emotions_db:
#                 emotion_id = self.emotions_db[detected_emotion_lower]['emotion_id']
#                 template_path = get_template_by_emotion_id(
#                     self.supabase_client,
#                     self.config.supabase_schema,
#                     memes_table,
#                     emotion_id
#                 )
#                 if template_path:
#                     logging.info(f"Found exact emotion match: {detected_emotion_lower}")
#                     return template_path
            
#             # If exact match fails, find nearest emotion
#             available_emotions = list(self.emotions_db.keys())
#             nearest_emotion = find_most_similar_text(
#                 detected_emotion_lower, 
#                 available_emotions, 
#                 self.config.similarity_threshold
#             )
            
#             if nearest_emotion and nearest_emotion != detected_emotion_lower:
#                 emotion_id = self.emotions_db[nearest_emotion]['emotion_id']
#                 template_path = get_template_by_emotion_id(
#                     self.supabase_client,
#                     self.config.supabase_schema,
#                     memes_table,
#                     emotion_id
#                 )
#                 if template_path:
#                     logging.info(f"Found similar emotion match: {detected_emotion_lower} -> {nearest_emotion}")
#                     return template_path
            
#             # If still no match, get random template
#             template_path = get_random_template(
#                 self.supabase_client,
#                 self.config.supabase_schema,
#                 memes_table
#             )
#             if template_path:
#                 logging.info(f"Used random template for emotion: {detected_emotion_lower}")
#                 return template_path
            
#             return None
            
#         except Exception as e:
#             logging.error(f"Error finding template for emotion '{detected_emotion}': {str(e)}")
#             return None

#     def match_templates_for_articles(self, processed_articles: List[Dict]) -> TemplateManagerArtifact:
#         """Match templates for all processed articles"""
#         try:
#             matched_templates = []
#             unmatched_emotions = []
#             emotions_matched = []
            
#             for i, article in enumerate(processed_articles):
#                 detected_emotion = article.get('emotion', '')
                
#                 if detected_emotion:
#                     template_path = self.find_template_by_emotion(detected_emotion)
                    
#                     if template_path:
#                         matched_templates.append(template_path)
#                         emotions_matched.append(detected_emotion)
#                         # Add template path to article
#                         article['template_image_path'] = template_path
#                         logging.info(f"Template matched for article {i+1}: {detected_emotion}")
#                     else:
#                         unmatched_emotions.append(detected_emotion)
#                         article['template_image_path'] = None
#                         logging.warning(f"No template found for article {i+1}: {detected_emotion}")
#                 else:
#                     unmatched_emotions.append("no_emotion")
#                     article['template_image_path'] = None
#                     logging.warning(f"No emotion detected for article {i+1}")
            
#             template_success_rate = (len(matched_templates) / len(processed_articles)) * 100 if processed_articles else 0
            
#             logging.info(f"Template matching completed: {len(matched_templates)}/{len(processed_articles)} templates matched ({template_success_rate:.1f}%)")
            
#             return TemplateManagerArtifact(
#                 matched_templates=matched_templates,
#                 template_success_rate=template_success_rate,
#                 emotions_matched=emotions_matched,
#                 unmatched_emotions=unmatched_emotions
#             )
            
#         except Exception as e:
#             logging.error(f"Error in match_templates_for_articles: {str(e)}")
#             raise CustomException(e, sys)

#     def get_available_emotions(self) -> List[str]:
#         """Get list of available emotions from database"""
#         return list(self.emotions_db.keys())


