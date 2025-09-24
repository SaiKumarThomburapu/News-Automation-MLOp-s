from supabase import Client
from typing import Dict, List, Optional
import sys
from src.logger import logging
from src.exceptions import CustomException

def load_emotions_from_database(supabase_client: Client, schema: str, table: str) -> Dict[str, Dict]:
    """Load emotions from Supabase database"""
    try:
        logging.info(f"Loading emotions from Supabase table: {table}")
        
        # For Supabase, if using a schema other than 'public', table should already include schema
        # If table already has schema prefix, use as-is, otherwise just use table name
        if '.' in table:
            # Table already has schema prefix
            response = supabase_client.from_(table).select('*').execute()
        else:
            # Just table name, let Supabase handle default schema
            response = supabase_client.from_(table).select('*').execute()
        
        if response.data:
            emotions_dict = {}
            for emotion in response.data:
                emotion_label = emotion['emotion_label'].lower()
                emotions_dict[emotion_label] = {
                    'emotion_id': emotion['emotion_id'],
                    'emotion_label': emotion['emotion_label'],
                    'description': emotion['description']
                }
            
            logging.info(f"Loaded {len(emotions_dict)} emotions from database")
            return emotions_dict
        else:
            logging.warning("No emotions found in database")
            return {}
            
    except Exception as e:
        logging.error(f"Error loading emotions from {table}: {str(e)}")
        # Return empty dict instead of raising exception for now
        return {}

def get_template_by_emotion_id(supabase_client: Client, schema: str, table: str, 
                              emotion_id: int) -> Optional[str]:
    """Get meme template by emotion ID"""
    try:
        logging.info(f"Getting template for emotion_id {emotion_id} from table: {table}")
        
        # Handle schema the same way
        if '.' in table:
            response = supabase_client.from_(table).select('*').eq('emotion_id', emotion_id).execute()
        else:
            response = supabase_client.from_(table).select('*').eq('emotion_id', emotion_id).execute()
        
        if response.data:
            import random
            selected_template = random.choice(response.data)
            return selected_template.get('image_path', '')
        return None
        
    except Exception as e:
        logging.error(f"Error getting template for emotion_id {emotion_id}: {str(e)}")
        return None

def get_random_template(supabase_client: Client, schema: str, table: str) -> Optional[str]:
    """Get random meme template when emotion matching fails"""
    try:
        logging.info(f"Getting random template from table: {table}")
        
        # Handle schema the same way
        if '.' in table:
            response = supabase_client.from_(table).select('*').limit(10).execute()
        else:
            response = supabase_client.from_(table).select('*').limit(10).execute()
        
        if response.data:
            import random
            selected_template = random.choice(response.data)
            return selected_template.get('image_path', '')
        return None
        
    except Exception as e:
        logging.error(f"Error getting random template: {str(e)}")
        return None




