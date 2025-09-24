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

from src.pipeline.news_pipeline import NewsPipeline

app = FastAPI(
    title="News Meme Pipeline API", 
    description="Single endpoint for complete news scraping and AI meme processing",
    version="2.0.0"
)

# Initialize pipeline on startup
def initialize_pipeline():
    """Initialize the complete pipeline"""
    try:
        # Check environment variables
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise Exception("Missing SUPABASE_URL or SUPABASE_KEY in .env file")
        
        # Initialize Supabase
        supabase_client = create_client(supabase_url, supabase_key)
        
        # Get Gemini API keys
        gemini_api_keys = [
            os.getenv('GEMINI_API_KEY_1'),
            os.getenv('GEMINI_API_KEY_2'),
            os.getenv('GEMINI_API_KEY_3'),
            os.getenv('GEMINI_API_KEY_4')
        ]
        
        valid_api_keys = [key for key in gemini_api_keys if key]
        
        if not valid_api_keys:
            raise Exception("No GEMINI_API_KEY found in .env file")
        
        # Initialize pipeline
        pipeline = NewsPipeline(valid_api_keys, supabase_client)
        
        print("✅ Pipeline initialized successfully!")
        print(f"   - Supabase: Connected")
        print(f"   - Gemini API Keys: {len(valid_api_keys)} available")
        
        return pipeline
        
    except Exception as e:
        print(f"❌ Pipeline initialization failed: {str(e)}")
        return None

# Initialize pipeline
news_pipeline = initialize_pipeline()

@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "api": "News Meme Pipeline",
        "version": "2.0.0",
        "description": "Complete MLOps pipeline for news scraping and AI meme generation",
        "status": "Ready" if news_pipeline else "Not initialized",
        "main_endpoint": "/process-news",
        "features": [
            "Scrapes categorized news (6 categories, 10 articles each)",
            "Downloads associated images",
            "Processes with AI for sarcastic content",
            "Matches emotion-based meme templates",
            "Returns comprehensive JSON output"
        ],
        "categories": ["politics", "movies", "entertainment", "sports", "business", "technology"]
    }

@app.get("/process-news")
def complete_news_pipeline():
    """
    🚀 COMPLETE PIPELINE ENDPOINT 
    
    Executes the full MLOps news meme generation pipeline:
    1. Scrapes news from multiple sources (categorized)
    2. Processes and ranks articles by buzz score
    3. Downloads associated images
    4. Processes articles with Gemini AI for sarcastic content
    5. Matches emotion-based meme templates
    6. Generates comprehensive output files
    
    Returns complete pipeline results with all generated data.
    """
    if not news_pipeline:
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
        print("🚀 STARTING COMPLETE NEWS MEME PIPELINE")
        print("="*80)
        
        # Execute complete pipeline
        result = news_pipeline.execute_complete_pipeline()
        
        print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*80 + "\n")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        # Clean error message
        clean_error = str(e)
        if "ALTS creds ignored" in clean_error:
            clean_error = clean_error.replace("ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.", "").strip()
        
        print(f"❌ Pipeline execution failed: {clean_error}")
        
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
    print("🎯 News Meme Pipeline API - Single Endpoint")
    print("="*80)
    
    if news_pipeline:
        print("✅ Pipeline Ready!")
        print("🚀 Visit: http://localhost:8000/process-news")
        print("\nPipeline Features:")
        print("  ⚡ Scrapes 60 categorized news articles")
        print("  🖼️  Downloads associated images")
        print("  🤖 AI-powered sarcastic content generation")
        print("  😊 Emotion-based meme template matching")
        print("  📊 Comprehensive JSON output")
    else:
        print("⚠️  Pipeline initialization failed")
        print("   Check your .env file configuration")
        print("   API will still start for debugging")
    
    print("="*80)
    print("Starting server on http://localhost:8000")
    print("="*80)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

