import os
import logging
import warnings

# SUPPRESS GOOGLE CLOUD WARNINGS - MUST BE AT THE TOP
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
warnings.filterwarnings("ignore", category=UserWarning, module="google.auth")
logging.getLogger('google').setLevel(logging.ERROR)
logging.getLogger('googleapiclient').setLevel(logging.ERROR)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from supabase import create_client, Client
from datetime import datetime

# Load environment variables
load_dotenv()

# Import only the main pipeline function
from src.pipeline.unified_news_pipeline import execute_complete_pipeline

app = FastAPI(
    title="News Meme AI Processing API", 
    description="Single endpoint for complete news scraping and AI meme processing pipeline",
    version="3.0.0"
)

# Global variables for pipeline configuration
supabase_client = None
gemini_api_keys = []

def initialize_pipeline():
    """Initialize the pipeline configuration"""
    global supabase_client, gemini_api_keys
    
    try:
        # Check environment variables
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise Exception("Missing SUPABASE_URL or SUPABASE_KEY in .env file")
        
        # Initialize Supabase
        supabase_client = create_client(supabase_url, supabase_key)
        
        # Configure client to use dc schema with headers
        supabase_client.postgrest.session.headers.update({'Accept-Profile': 'dc'})
        
        print(" SUCCESS: Configured Supabase client to use 'dc' schema with headers")
        
        # Verify schema access works
        try:
            emotions_result = supabase_client.table('emotions').select('*').limit(1).execute()
            memes_result = supabase_client.table('memes_dc').select('*').limit(1).execute()
            
            print(f" SUCCESS: emotions table accessible - {len(emotions_result.data)} records")
            print(f" SUCCESS: memes_dc table accessible - {len(memes_result.data)} records")
            
            if emotions_result.data:
                sample = emotions_result.data[0]
                print(f" Sample emotion: {sample.get('emotion_label', 'NO_LABEL')}")
            
            if memes_result.data:
                sample_meme = memes_result.data[0]
                print(f" Sample meme: {sample_meme.get('meme_id', 'NO_ID')[:10]}...")
            
        except Exception as verify_e:
            print(f" Schema verification failed: {str(verify_e)}")
            raise Exception(f"Schema access verification failed: {str(verify_e)}")
        
        # Get Gemini API keys
        api_keys = [
            os.getenv('GEMINI_API_KEY_1'),
            os.getenv('GEMINI_API_KEY_2'),
            os.getenv('GEMINI_API_KEY_3'),
            os.getenv('GEMINI_API_KEY_4')
        ]
        
        gemini_api_keys = [key for key in api_keys if key]
        
        if not gemini_api_keys:
            raise Exception("No GEMINI_API_KEY found in .env file")
        
        print(" Pipeline configuration initialized successfully!")
        print(f"   - Supabase: Connected to 'dc' schema")
        print(f"   - Gemini API Keys: {len(gemini_api_keys)} available")
        
        return True
        
    except Exception as e:
        print(f" Pipeline initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# Initialize pipeline configuration
pipeline_ready = initialize_pipeline()

@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "api": "News Meme AI Processing API",
        "version": "3.0.0",
        "description": "Complete MLOps pipeline for news scraping and AI meme generation",
        "status": "Ready" if pipeline_ready else "Not initialized",
        "endpoint": "/process",
        "features": [
            "Scrapes categorized news from multiple sources",
            "Downloads associated images",
            "Processes articles with AI for sarcastic content",
            "Matches emotion-based meme templates from dc schema",
            "Downloads templates from Supabase storage",
            "Overlays dialogues on templates with dynamic font sizing",
            "Returns final memes as base64 in JSON"
        ],
        "categories": ["politics", "movies", "entertainment", "sports", "business", "technology"],
        "supabase_schema": "dc",
        "architecture": "Pure functional approach"
    }

@app.get("/process")
def process_complete_pipeline():
    """
    COMPLETE News Meme Generation Pipeline
    
    This single endpoint executes the entire end-to-end pipeline:
    
    PHASE 1 - NEWS SCRAPING:
    1. Scrapes categorized news from multiple Indian sources
    2. Processes and ranks articles by buzz score
    3. Downloads associated images
    4. Saves clean categorized news data
    
    PHASE 2 - AI PROCESSING & MEME GENERATION:
    5. Processes articles with Gemini AI for emotion detection and sarcastic dialogues
    6. Matches emotion-based meme templates from Supabase dc schema
    7. Downloads templates from Supabase storage
    8. Overlays dialogues on templates with dynamic font sizing
    9. Generates final memes as base64 in JSON output
    10. Saves complete processed memes data
    
    Returns comprehensive pipeline results with detailed statistics.
    """
    if not pipeline_ready:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Pipeline not initialized",
                "message": "Check your .env configuration for Supabase and Gemini API keys",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    try:
        print("\n" + "="*80)
        print(" STARTING COMPLETE NEWS MEME GENERATION PIPELINE")
        print("="*80)
        
        # Execute the complete pipeline - does everything internally:
        # - scrape_and_process_news() 
        # - process_with_ai()
        # - All saving and processing steps
        result = execute_complete_pipeline(gemini_api_keys, supabase_client)
        
        print(" COMPLETE PIPELINE FINISHED SUCCESSFULLY!")
        print("="*80 + "\n")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        clean_error = str(e)
        if "ALTS creds ignored" in clean_error:
            clean_error = clean_error.replace("ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.", "").strip()
        
        print(f" Pipeline execution failed: {clean_error}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Pipeline execution failed",
                "message": clean_error,
                "timestamp": datetime.now().isoformat(),
                "suggestion": "Check logs for detailed error information"
            }
        )

if __name__ == "__main__":
    import uvicorn
    
    print("="*80)
    print(" News Meme AI Processing API - Complete Pipeline")
    print("="*80)
    
    if pipeline_ready:
        print(" Pipeline Ready!")
        print(" Single Endpoint: http://localhost:8000/process")
        print(" API Info: http://localhost:8000/")
        print("\n Complete Pipeline Process:")
        print("   Phase 1: News Scraping & Image Download")
        print("   Phase 2: AI Processing & Meme Generation")
        print("   Saves all data and generates final memes as base64")
        print("\n Features:")
        print("  Pure functional architecture")
        print("  Scrapes 60+ categorized news articles")
        print("  AI-powered sarcastic content generation")
        print("  Emotion-based template matching")
        print("  Dynamic dialogue overlay with font sizing")
        print("  Final memes returned as base64 in JSON")
    else:
        print("Pipeline initialization failed")
        print("   Check your .env file configuration")
        print("   API will still start for debugging")
    
    print("="*80)
    print(" Starting server on http://localhost:8000")
    print("="*80)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)








