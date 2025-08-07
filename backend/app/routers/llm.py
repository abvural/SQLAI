"""
LLM management router
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/llm",
    tags=["llm"]
)

@router.get("/status")
async def get_llm_status() -> Dict[str, Any]:
    """Get the status of LLM models and Ollama service"""
    try:
        # Check Ollama service
        async with httpx.AsyncClient() as client:
            # Get Ollama version
            try:
                version_resp = await client.get("http://localhost:11434/api/version", timeout=5.0)
                ollama_version = version_resp.json().get("version", "unknown")
                ollama_running = True
            except:
                ollama_version = None
                ollama_running = False
            
            # Get available models
            models = []
            if ollama_running:
                try:
                    models_resp = await client.get("http://localhost:11434/api/tags", timeout=5.0)
                    models_data = models_resp.json()
                    
                    for model in models_data.get("models", []):
                        models.append({
                            "name": model.get("name"),
                            "size": model.get("size"),
                            "size_gb": round(model.get("size", 0) / (1024**3), 2),
                            "modified": model.get("modified_at"),
                            "digest": model.get("digest")[:12] + "..." if model.get("digest") else None
                        })
                except Exception as e:
                    logger.error(f"Error fetching models: {e}")
            
            # Check if required models are available
            required_models = {
                "mistral": "mistral:7b-instruct-q4_K_M",
                "sqlcoder": "sqlcoder:latest"
            }
            
            available_models = {m["name"] for m in models}
            models_status = {}
            
            for key, model_name in required_models.items():
                models_status[key] = {
                    "required": model_name,
                    "available": model_name in available_models,
                    "status": "ready" if model_name in available_models else "missing"
                }
            
            # Overall status
            all_models_ready = all(m["available"] for m in models_status.values())
            
            return {
                "status": "ready" if ollama_running and all_models_ready else "partial" if ollama_running else "offline",
                "timestamp": datetime.now().isoformat(),
                "ollama": {
                    "running": ollama_running,
                    "version": ollama_version,
                    "endpoint": "http://localhost:11434"
                },
                "models": {
                    "available": models,
                    "required": models_status,
                    "all_ready": all_models_ready
                },
                "capabilities": {
                    "natural_language": all_models_ready,
                    "sql_generation": models_status.get("sqlcoder", {}).get("available", False),
                    "turkish_support": True,
                    "streaming": True
                }
            }
            
    except Exception as e:
        logger.error(f"Error checking LLM status: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "ollama": {
                "running": False,
                "version": None,
                "endpoint": "http://localhost:11434"
            },
            "models": {
                "available": [],
                "required": {},
                "all_ready": False
            },
            "capabilities": {
                "natural_language": False,
                "sql_generation": False,
                "turkish_support": False,
                "streaming": False
            }
        }

@router.post("/pull/{model_name}")
async def pull_model(model_name: str) -> Dict[str, Any]:
    """Pull/download a model from Ollama registry"""
    try:
        async with httpx.AsyncClient() as client:
            # Start model pull
            response = await client.post(
                "http://localhost:11434/api/pull",
                json={"name": model_name},
                timeout=None  # No timeout for large downloads
            )
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "message": f"Model {model_name} pulled successfully",
                    "model": model_name
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to pull model: {response.text}"
                )
                
    except httpx.RequestError as e:
        logger.error(f"Error pulling model {model_name}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Ollama service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error pulling model {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@router.post("/test")
async def test_llm_generation() -> Dict[str, Any]:
    """Test LLM generation with a simple prompt"""
    try:
        async with httpx.AsyncClient() as client:
            # Test with Mistral model
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "mistral:7b-instruct-q4_K_M",
                    "prompt": "Hello, respond with a simple greeting in Turkish.",
                    "stream": False
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "success",
                    "model": "mistral:7b-instruct-q4_K_M",
                    "response": result.get("response", ""),
                    "generation_time": result.get("total_duration", 0) / 1e9,  # Convert to seconds
                    "test_passed": True
                }
            else:
                return {
                    "status": "error",
                    "error": f"Generation failed: {response.text}",
                    "test_passed": False
                }
                
    except Exception as e:
        logger.error(f"Error testing LLM: {e}")
        return {
            "status": "error",
            "error": str(e),
            "test_passed": False
        }