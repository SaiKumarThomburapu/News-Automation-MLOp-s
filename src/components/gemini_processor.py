import os
import json
import re
import time
import warnings
import google.generativeai as genai
import sys
from typing import List, Dict, Optional
from src.entity.artifacts import GeminiProcessorArtifact
from src.entity.config_entity import GeminiProcessorConfig, ConfigEntity
from src.logger import logging
from src.exceptions import CustomException
from src.utils.api_utils import APIKeyRotator, apply_rate_limiting

# Suppress Google Cloud warnings
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
warnings.filterwarnings("ignore", category=UserWarning, module="google.auth")

class GeminiProcessor:
    def __init__(self, api_keys: List[str]):
        self.config = GeminiProcessorConfig(config=ConfigEntity())
        
        # Filter out None values from API keys
        valid_api_keys = [key for key in api_keys if key]
        if not valid_api_keys:
            raise CustomException("No valid Gemini API keys provided", sys)
        
        # Initialize API key rotator
        self.api_rotator = APIKeyRotator(
            valid_api_keys, 
            self.config.max_calls_per_key_per_minute
        )
        
        logging.info(f"GeminiProcessor initialized with {len(valid_api_keys)} API keys")

    def create_comprehensive_prompt(self, news_content: str, emotions_list: List[str]) -> str:
        """Create comprehensive prompt for Gemini API"""
        emotion_options = '\n'.join([f"- {emotion}" for emotion in emotions_list])
        
        prompt = f"""
You are a sarcastic, witty social media content creator and news analyst. Process this news article and provide ALL the following information in a single response:

NEWS CONTENT: "{news_content}"

Provide ALL the following in JSON format:

1. DESCRIPTION: Create a SARCASTIC, BUZZY 2-3 line description
   - Make it viral-worthy and engaging
   - Use sarcastic tone and witty commentary
   - No emojis, just pure sarcastic wit
   - Maximum 3 lines that people would want to share
   - Think like a roast comedian analyzing news

2. EMOTION: After reading your sarcastic description, identify the dominant emotion from these options:
{emotion_options}
   Return ONLY the emotion label in lowercase.

3. CATEGORY: Based on your description, categorize into ONE from: politics, entertainment, movies, sports, business, technology, crime
   - Read your own description first, then categorize
   - If about films/cinema/actors/bollywood → "movies"
   - If about TV/music/celebrities/awards → "entertainment"
   - If about police/arrest/murder/fraud/court → "crime"
   - If about government/elections/politicians → "politics"

4. DIALOGUES: Create 2 SARCASTIC meme dialogues (max 8 words each)
   - Use formats: "When...", "Me:", "POV:", "Everyone:", "Meanwhile:"
   - Make them hilariously sarcastic and relatable
   - Each dialogue MUST be maximum 8 words
   - Think like a meme creator roasting the situation

5. HASHTAGS: Generate 6-8 sarcastic/buzzy hashtags
   - Mix trending tags with sarcastic ones
   - Include category-specific tags
   - Make them shareable and viral-worthy

RETURN EVERYTHING in this EXACT JSON structure:
{{
    "description": "Sarcastic line 1\\nSarcastic line 2\\nSarcastic line 3 (if needed)",
    "emotion": "emotion_label",
    "category": "category_name", 
    "dialogues": ["sarcastic dialogue 1 (max 8 words)", "sarcastic dialogue 2 (max 8 words)"],
    "hashtags": ["#SarcasticTag1", "#BuzzyTag2", "#CategoryTag", "#Trending", "#ViralTag", "#SarcasmLevel100"]
}}

Analyze and create sarcastic content for this news:
"""
        return prompt

    def safe_gemini_call(self, prompt: str) -> str:
        """Make Gemini API call with proper key rotation and error handling"""
        for attempt in range(self.config.max_gemini_retries):
            try:
                key_index = self.api_rotator.get_next_available_key_index()
                api_key = self.api_rotator.get_api_key(key_index)
                
                logging.info(f"Using API Key #{key_index + 1}")
                
                # Configure Gemini with error suppression
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(self.config.gemini_model_name)
                
                # Record the call
                self.api_rotator.record_api_call(key_index)
                
                # Make the API call
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    response = model.generate_content(prompt)
                
                # Apply rate limiting
                apply_rate_limiting(self.config.api_call_delay)
                
                return response.text.strip()
                
            except Exception as e:
                error_msg = str(e)
                # Clean Google Cloud warnings from error message
                if "ALTS creds ignored" not in error_msg:
                    logging.warning(f"API Key #{key_index + 1} failed: {error_msg}")
                
                if attempt < self.config.max_gemini_retries - 1:
                    time.sleep(5)
                else:
                    clean_error = error_msg.replace("ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.", "").strip()
                    raise CustomException(f"All API attempts failed: {clean_error}", sys)

    def parse_gemini_response(self, response: str) -> Optional[Dict]:
        """Parse JSON response from Gemini"""
        try:
            # Try to extract JSON from response
            json_pattern = r'\{.*?\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            if json_match:
                json_text = json_match.group(0)
                parsed = json.loads(json_text)
                
                required_fields = ['description', 'emotion', 'category', 'dialogues', 'hashtags']
                if all(key in parsed for key in required_fields):
                    # Ensure dialogues are max 8 words each
                    if 'dialogues' in parsed and isinstance(parsed['dialogues'], list):
                        cleaned_dialogues = []
                        for dialogue in parsed['dialogues'][:2]:
                            words = str(dialogue).split()
                            if len(words) <= 8:
                                cleaned_dialogues.append(' '.join(words))
                            else:
                                cleaned_dialogues.append(' '.join(words[:8]))
                        parsed['dialogues'] = cleaned_dialogues
                    
                    logging.info("Successfully parsed Gemini response")
                    return parsed
                    
            return self.manual_parse_response(response)
            
        except json.JSONDecodeError:
            return self.manual_parse_response(response)
        except Exception as e:
            logging.error(f"Error parsing Gemini response: {str(e)}")
            return None

    def manual_parse_response(self, response: str) -> Optional[Dict]:
        """Manually parse response if JSON parsing fails"""
        try:
            result = {}
            
            # Extract description
            desc_patterns = [
                r'"?description"?\s*:\s*"([^"]+)"',
                r'description[:\s]+(.+?)(?=emotion|category|\n\n)',
            ]
            
            for pattern in desc_patterns:
                desc_match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                if desc_match:
                    result['description'] = desc_match.group(1).strip()
                    break
            
            if 'description' not in result:
                result['description'] = "Another predictable news story that surprises absolutely no one\nBecause apparently this passes for journalism these days\nStay tuned for more earth-shattering updates"
            
            # Extract emotion
            emotion_match = re.search(r'"?emotion"?\s*:\s*"?(\w+)"?', response, re.IGNORECASE)
            result['emotion'] = emotion_match.group(1).lower() if emotion_match else 'sarcasm'
            
            # Extract category
            category_match = re.search(r'"?category"?\s*:\s*"?(\w+)"?', response, re.IGNORECASE)
            result['category'] = category_match.group(1) if category_match else 'entertainment'
            
            # Extract dialogues
            dialogues = re.findall(r'"([^"]+)"', response)
            sarcastic_candidates = [d for d in dialogues if 2 <= len(d.split()) <= 10]
            result['dialogues'] = sarcastic_candidates[:2] if len(sarcastic_candidates) >= 2 else ["When news tries to surprise us", "Everyone: Been there done that"]
            
            # Extract hashtags
            hashtags = re.findall(r'#\w+', response)
            result['hashtags'] = hashtags[:6] if hashtags else ["#Sarcasm", "#News", "#Reality", "#NoSurprise", "#Trending", "#Buzzy"]
            
            return result
            
        except Exception as e:
            logging.error(f"Manual parsing failed: {str(e)}")
            return None

    def process_single_article(self, article: Dict, emotions_list: List[str]) -> Optional[Dict]:
        """Process single article with Gemini API"""
        try:
            content = article.get('content', '')
            url = article.get('url', '')
            
            # Create comprehensive prompt
            prompt = self.create_comprehensive_prompt(content, emotions_list)
            
            # Make API call
            response = self.safe_gemini_call(prompt)
            parsed_data = self.parse_gemini_response(response)
            
            if parsed_data:
                # Create final result with all requested fields
                result = {
                    "content": content,
                    "description": parsed_data.get('description', ''),
                    "category": parsed_data.get('category', 'entertainment'),
                    "emotion": parsed_data.get('emotion', '').lower(),
                    "hashtags": parsed_data.get('hashtags', []),
                    "dialogues": parsed_data.get('dialogues', []),
                    "url": url,
                    "image_path": article.get('image_path')
                }
                
                return result
            else:
                raise CustomException("Failed to parse Gemini response", sys)
                
        except Exception as e:
            clean_error = str(e).replace("ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.", "").strip()
            logging.error(f"Error processing article: {clean_error}")
            return None

    def process_articles(self, categorized_articles: Dict[str, List[Dict]], emotions_list: List[str]) -> GeminiProcessorArtifact:
        """Process all articles with Gemini AI"""
        try:
            processed_content = []
            failed_articles = []
            total_api_calls = 0
            
            # Flatten articles for processing
            all_articles = []
            for category, articles in categorized_articles.items():
                all_articles.extend(articles)
            
            total_articles = len(all_articles)
            logging.info(f"Processing {total_articles} articles with Gemini AI")
            
            for i, article in enumerate(all_articles, 1):
                logging.info(f"Processing article {i}/{total_articles}")
                
                try:
                    result = self.process_single_article(article, emotions_list)
                    total_api_calls += 1
                    
                    if result:
                        processed_content.append(result)
                        logging.info(f"SUCCESS! Article {i} processed")
                    else:
                        failed_articles.append(article.get('url', f'article_{i}'))
                        logging.warning(f"FAILED to process article {i}")
                        
                except Exception as e:
                    total_api_calls += 1
                    failed_articles.append(article.get('url', f'article_{i}'))
                    clean_error = str(e).replace("ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.", "").strip()
                    logging.error(f"Error processing article {i}: {clean_error}")
                    continue
                
                # Show progress
                success_rate = (len(processed_content) / i) * 100 if i > 0 else 0
                logging.info(f"Progress: {i}/{total_articles} | Success: {len(processed_content)} ({success_rate:.1f}%)")
            
            final_success_rate = (len(processed_content) / total_articles) * 100 if total_articles > 0 else 0
            
            logging.info(f"Gemini processing completed: {len(processed_content)}/{total_articles} articles processed ({final_success_rate:.1f}%)")
            
            return GeminiProcessorArtifact(
                processed_content=processed_content,
                total_api_calls=total_api_calls,
                success_rate=final_success_rate,
                failed_articles=failed_articles
            )
            
        except Exception as e:
            logging.error(f"Error in process_articles: {str(e)}")
            raise CustomException(e, sys)
