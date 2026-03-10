from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from news_generator import generate_combined_article
import uvicorn
import anyio  # For running sync code in a thread pool

app = FastAPI(title="NewsletterAI Generation Service")

# 1. Enable CORS for local development and Next.js communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerationRequest(BaseModel):
    article_ids: List[str]
    user_id: str = None  # Optional field with default None

@app.post("/generate-article")
async def generate_article_endpoint(request: GenerationRequest):
    """
    Endpoint to combine multiple raw articles into a single news article.
    Runs the blocking AI logic in a thread to keep the API responsive.
    """
    print(f"Received generation request for IDs: {request.article_ids} | User: {request.user_id}")
    
    try:
        # 2. Run the blocking function in a separate thread so the API stays responsive
        result = await anyio.to_thread.run_sync(
            generate_combined_article, 
            request.article_ids, 
            request.user_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected internal error: {str(e)}")
    
    if "error" in result:
        # Distinguish between 404 (not found) and 500 (AI/DB error)
        status_code = 404 if "No articles found" in result["error"] else 500
        raise HTTPException(status_code=status_code, detail=result["error"])
        
    return result

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
