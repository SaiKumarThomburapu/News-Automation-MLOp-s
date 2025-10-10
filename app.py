import os
import sys
import uuid
import shutil
import tempfile
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
 
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, validator
 
from src.pipeline.full_pipeline import upload_service
from src.logger import logging
from src.constants import INDIC_MODEL_NAME, WHISPER_MODEL_NAME, OUTPUT_DIR
from src.entity.config_entity import ConfigEntity
import src.components.language_detector as lang_mod
import src.components.transcriber as trans_mod
 
# -----------------------------
# App Initialization
# -----------------------------
app = FastAPI(
    title="Auto Caption Generator API",
    description="Video to Caption generation using IndicConformer + Whisper fallback for English",
    version="3.2.0"
)
 
# Ensure artifacts folder exists
ARTIFACTS_DIR = OUTPUT_DIR
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
 
# Temp dir for per-request uploads
BASE_TEMP_DIR = os.path.join(ARTIFACTS_DIR, "temp_uploads")
os.makedirs(BASE_TEMP_DIR, exist_ok=True)
 
# ThreadPoolExecutor for blocking tasks
executor = ThreadPoolExecutor(max_workers=4)
 
# In-memory task storage
task_data: Dict[str, Dict[str, Any]] = {}
 
# -----------------------------
# Global Exception Handlers
# -----------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}")
    logging.error(traceback.format_exc())
    return JSONResponse(status_code=500, content={"error": "internal_server_error", "detail": str(exc)})
 
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"Request validation error: {exc}")
    logging.error(traceback.format_exc())
    return JSONResponse(status_code=422, content={"error": "validation_error", "detail": exc.errors()})
 
# -----------------------------
# Pydantic Upload Config
# -----------------------------
class UploadConfig(BaseModel):
    file_size_limit: int = 100 * 1024 * 1024  # default 100 MB
 
    @validator("file_size_limit")
    def positive_limit(cls, v):
        if v <= 0:
            raise ValueError("file_size_limit must be positive")
        return v
 
async def get_upload_config(file_size_limit: int = Form(100*1024*1024)) -> UploadConfig:
    return UploadConfig(file_size_limit=file_size_limit)
 
# -----------------------------
# Utility Functions
# -----------------------------
def make_temp_dir() -> str:
    return tempfile.mkdtemp(prefix="req_", dir=BASE_TEMP_DIR)
 
async def save_upload_to_dir(upload: UploadFile, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, upload.filename)
    contents = await upload.read()
    with open(dest_path, "wb") as f:
        f.write(contents)
    await upload.seek(0)
    return dest_path
 
def run_async_in_executor(coro_func, *args, **kwargs):
    """
    Wrapper to run an async coroutine in ThreadPoolExecutor safely.
    """
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, lambda: asyncio.run(coro_func(*args, **kwargs)))
 
def cleanup_temp_dir(path: str):
    try:
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
            logging.info(f"Cleaned up temp dir: {path}")
    except Exception as e:
        logging.error(f"Error cleaning temp dir {path}: {e}")
        logging.error(traceback.format_exc())
 
def parse_srt_to_json(srt_path: str) -> List[Dict[str, Any]]:
    """
    Parses an SRT file into JSON format:
    [
        {"index": 1, "time": "00:00:00,000 --> 00:00:06,037", "dialogue": "text"},
        ...
    ]
    """
    if not os.path.exists(srt_path):
        return []
 
    result = []
    with open(srt_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
 
    index, time, text = None, None, []
    for line in lines + [""]:  # Add empty line at end to flush last block
        line = line.strip()
        if line.isdigit():
            index = int(line)
        elif "-->" in line:
            time = line
        elif line == "":
            if index is not None and time is not None and text:
                dialogue = " ".join(text)
                result.append({"index": index, "time": time, "dialogue": dialogue})
            index, time, text = None, None, []
        else:
            text.append(line)
    return result
 
# -----------------------------
# Startup Event: Load Models
# -----------------------------
indic_model = None
whisper_model = None
 
@app.on_event("startup")
async def startup_event():
    global indic_model, whisper_model
    try:
        logging.info("Loading IndicConformer model...")
        from transformers import AutoModel
        import whisper
 
        indic_model = AutoModel.from_pretrained(INDIC_MODEL_NAME, trust_remote_code=True)
        whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
 
        # Inject models into components
        lang_mod.indic_model = indic_model
        lang_mod.whisper_model = whisper_model
        trans_mod.indic_model = indic_model
        trans_mod.whisper_model = whisper_model
 
        logging.info("Models loaded successfully")
    except Exception as e:
        logging.error(f"Model loading failed: {str(e)}")
 
# -----------------------------
# Upload Endpoint
# -----------------------------
@app.post("/upload-video/")
async def upload_video(file: UploadFile = File(...), config: UploadConfig = Depends(get_upload_config)):
    global indic_model, whisper_model
    if not indic_model or not whisper_model:
        raise HTTPException(status_code=503, detail="Models not loaded yet")
 
    tempdir = make_temp_dir()
    try:
        # File size validation
        contents = await file.read()
        if len(contents) > config.file_size_limit:
            await file.close()
            cleanup_temp_dir(tempdir)
            raise HTTPException(status_code=400, detail=f"File exceeds size limit ({config.file_size_limit} bytes)")
        await file.seek(0)
 
        saved_video_path = await save_upload_to_dir(file, tempdir)
 
        # Run async upload_service safely in executor
        result = await run_async_in_executor(upload_service, file, task_data)
 
        # Store tempdir reference for cleanup
        if "task_id" in result:
            task_id = result["task_id"]
            task_data[task_id]["video_path"] = saved_video_path
            task_data[task_id]["tempdir"] = tempdir
 
        # Parse SRT file to JSON
        srt_path = result.get("srt_file_path")
        if srt_path and os.path.exists(srt_path):
            srt_json = parse_srt_to_json(srt_path)
            result["srt_json"] = srt_json
            # Remove artifacts after reading
            cleanup_temp_dir(tempdir)
            try:
                os.remove(srt_path)
            except:
                pass
 
        return JSONResponse(content=result, status_code=200)
 
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Upload error: {e}")
        logging.error(traceback.format_exc())
        cleanup_temp_dir(tempdir)
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        try:
            await file.close()
        except Exception:
            pass
 
# -----------------------------
# Task Status Endpoint
# -----------------------------
@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in task_data:
        return JSONResponse(status_code=404, content={"error": "task not found"})
    data = task_data[task_id]
    return {
        "status": data.get("status"),
        "language": data.get("language"),
        "model_used": data.get("model_used"),
        "srt_file_path": data.get("srt_file_path"),
        "error": data.get("error")
    }
 
# -----------------------------
# Health Check
# -----------------------------
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
 
# -----------------------------
# Shutdown Cleanup
# -----------------------------
@app.on_event("shutdown")
async def shutdown_event():
    try:
        executor.shutdown(wait=True)
    except Exception as e:
        logging.error(f"Executor shutdown failed: {e}")
    # Cleanup all temp directories
    try:
        for name in os.listdir(BASE_TEMP_DIR):
            path = os.path.join(BASE_TEMP_DIR, name)
            cleanup_temp_dir(path)
    except Exception as e:
        logging.error(f"Final cleanup failed: {e}")










# import os
# import logging
# import warnings

# # SUPPRESS GOOGLE CLOUD WARNINGS - MUST BE AT THE TOP
# os.environ['GRPC_VERBOSITY'] = 'ERROR'
# os.environ['GLOG_minloglevel'] = '2'
# warnings.filterwarnings("ignore", category=UserWarning, module="google.auth")
# logging.getLogger('google').setLevel(logging.ERROR)
# logging.getLogger('googleapiclient').setLevel(logging.ERROR)

# from dotenv import load_dotenv
# from fastapi import FastAPI, HTTPException
# from fastapi.responses import JSONResponse
# from supabase import create_client, Client
# from datetime import datetime

# # Load environment variables
# load_dotenv()

# # Import only the main pipeline function
# from src.pipeline.unified_news_pipeline import execute_complete_pipeline

# app = FastAPI(
#     title="News Meme AI Processing API", 
#     description="Single endpoint for complete news scraping and AI meme processing pipeline",
#     version="3.0.0"
# )

# # Global variables for pipeline configuration
# supabase_client = None
# gemini_api_keys = []

# def initialize_pipeline():
#     """Initialize the pipeline configuration"""
#     global supabase_client, gemini_api_keys
    
#     try:
#         # Check environment variables
#         supabase_url = os.getenv('SUPABASE_URL')
#         supabase_key = os.getenv('SUPABASE_KEY')
        
#         if not supabase_url or not supabase_key:
#             raise Exception("Missing SUPABASE_URL or SUPABASE_KEY in .env file")
        
#         # Initialize Supabase
#         supabase_client = create_client(supabase_url, supabase_key)
        
#         # Configure client to use dc schema with headers
#         supabase_client.postgrest.session.headers.update({'Accept-Profile': 'dc'})
        
#         print(" SUCCESS: Configured Supabase client to use 'dc' schema with headers")
        
#         # Verify schema access works
#         try:
#             emotions_result = supabase_client.table('emotions').select('*').limit(1).execute()
#             memes_result = supabase_client.table('memes_dc').select('*').limit(1).execute()
            
#             print(f" SUCCESS: emotions table accessible - {len(emotions_result.data)} records")
#             print(f" SUCCESS: memes_dc table accessible - {len(memes_result.data)} records")
            
#             if emotions_result.data:
#                 sample = emotions_result.data[0]
#                 print(f" Sample emotion: {sample.get('emotion_label', 'NO_LABEL')}")
            
#             if memes_result.data:
#                 sample_meme = memes_result.data[0]
#                 print(f" Sample meme: {sample_meme.get('meme_id', 'NO_ID')[:10]}...")
            
#         except Exception as verify_e:
#             print(f" Schema verification failed: {str(verify_e)}")
#             raise Exception(f"Schema access verification failed: {str(verify_e)}")
        
#         # Get Gemini API keys
#         api_keys = [
#             os.getenv('GEMINI_API_KEY_1'),
#             os.getenv('GEMINI_API_KEY_2'),
#             os.getenv('GEMINI_API_KEY_3'),
#             os.getenv('GEMINI_API_KEY_4')
#         ]
        
#         gemini_api_keys = [key for key in api_keys if key]
        
#         if not gemini_api_keys:
#             raise Exception("No GEMINI_API_KEY found in .env file")
        
#         print(" Pipeline configuration initialized successfully!")
#         print(f"   - Supabase: Connected to 'dc' schema")
#         print(f"   - Gemini API Keys: {len(gemini_api_keys)} available")
        
#         return True
        
#     except Exception as e:
#         print(f" Pipeline initialization failed: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         return False

# # Initialize pipeline configuration
# pipeline_ready = initialize_pipeline()

# @app.get("/")
# def root():
#     """Root endpoint with API information"""
#     return {
#         "api": "News Meme AI Processing API",
#         "version": "3.0.0",
#         "description": "Complete MLOps pipeline for news scraping and AI meme generation",
#         "status": "Ready" if pipeline_ready else "Not initialized",
#         "endpoint": "/process",
#         "features": [
#             "Scrapes categorized news from multiple sources",
#             "Downloads associated images",
#             "Processes articles with AI for sarcastic content",
#             "Matches emotion-based meme templates from dc schema",
#             "Downloads templates from Supabase storage",
#             "Overlays dialogues on templates with dynamic font sizing",
#             "Returns final memes as base64 in JSON"
#         ],
#         "categories": ["politics", "movies", "entertainment", "sports", "business", "technology"],
#         "supabase_schema": "dc",
#         "architecture": "Pure functional approach"
#     }

# @app.get("/process")
# def process_complete_pipeline():
#     """
#     COMPLETE News Meme Generation Pipeline
    
#     This single endpoint executes the entire end-to-end pipeline:
    
#     PHASE 1 - NEWS SCRAPING:
#     1. Scrapes categorized news from multiple Indian sources
#     2. Processes and ranks articles by buzz score
#     3. Downloads associated images
#     4. Saves clean categorized news data
    
#     PHASE 2 - AI PROCESSING & MEME GENERATION:
#     5. Processes articles with Gemini AI for emotion detection and sarcastic dialogues
#     6. Matches emotion-based meme templates from Supabase dc schema
#     7. Downloads templates from Supabase storage
#     8. Overlays dialogues on templates with dynamic font sizing
#     9. Generates final memes as base64 in JSON output
#     10. Saves complete processed memes data
    
#     Returns comprehensive pipeline results with detailed statistics.
#     """
#     if not pipeline_ready:
#         raise HTTPException(
#             status_code=503,
#             detail={
#                 "error": "Pipeline not initialized",
#                 "message": "Check your .env configuration for Supabase and Gemini API keys",
#                 "timestamp": datetime.now().isoformat()
#             }
#         )
    
#     try:
#         print("\n" + "="*80)
#         print(" STARTING COMPLETE NEWS MEME GENERATION PIPELINE")
#         print("="*80)
        
#         # Execute the complete pipeline - does everything internally:
#         # - scrape_and_process_news() 
#         # - process_with_ai()
#         # - All saving and processing steps
#         result = execute_complete_pipeline(gemini_api_keys, supabase_client)
        
#         print(" COMPLETE PIPELINE FINISHED SUCCESSFULLY!")
#         print("="*80 + "\n")
        
#         return JSONResponse(content=result)
        
#     except Exception as e:
#         clean_error = str(e)
#         if "ALTS creds ignored" in clean_error:
#             clean_error = clean_error.replace("ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.", "").strip()
        
#         print(f" Pipeline execution failed: {clean_error}")
        
#         raise HTTPException(
#             status_code=500,
#             detail={
#                 "error": "Pipeline execution failed",
#                 "message": clean_error,
#                 "timestamp": datetime.now().isoformat(),
#                 "suggestion": "Check logs for detailed error information"
#             }
#         )

# if __name__ == "__main__":
#     import uvicorn
    
#     print("="*80)
#     print(" News Meme AI Processing API - Complete Pipeline")
#     print("="*80)
    
#     if pipeline_ready:
#         print(" Pipeline Ready!")
#         print(" Single Endpoint: http://localhost:8000/process")
#         print(" API Info: http://localhost:8000/")
#         print("\n Complete Pipeline Process:")
#         print("   Phase 1: News Scraping & Image Download")
#         print("   Phase 2: AI Processing & Meme Generation")
#         print("   Saves all data and generates final memes as base64")
#         print("\n Features:")
#         print("  Pure functional architecture")
#         print("  Scrapes 60+ categorized news articles")
#         print("  AI-powered sarcastic content generation")
#         print("  Emotion-based template matching")
#         print("  Dynamic dialogue overlay with font sizing")
#         print("  Final memes returned as base64 in JSON")
#     else:
#         print("Pipeline initialization failed")
#         print("   Check your .env file configuration")
#         print("   API will still start for debugging")
    
#     print("="*80)
#     print(" Starting server on http://localhost:8000")
#     print("="*80)
    
#     uvicorn.run(app, host="0.0.0.0", port=8000)








