import logging
import uuid
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agent_graph import run_devops_workflow
from database import create_db_and_tables

# Configure Enterprise-Grade Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("AutoOps.Gateway")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Ensures seamless database initialization and graceful degradation.
    """
    logger.info("Initializing AutoOps Database & ORM Mapping...")
    create_db_and_tables()
    logger.info("Database initialized successfully.")
    yield
    logger.info("Initiating graceful shutdown of AutoOps components...")

app = FastAPI(
    title="AutoOps: Autonomous AI Engineering Swarm",
    description=(
        "A decentralized, event-driven agentic LLM architecture orchestrating "
        "end-to-end DevOps automation, SRE, and infrastructure cost optimization. "
        "Engineered for zero-defect deployments and sub-5-minute MTTR."
    ),
    version="2.0.0-enterprise",
    contact={
        "name": "Ismail Sajid",
        "url": "https://github.com/IsmailSajid",
    },
    lifespan=lifespan
)

# CORS Middleware for secure cross-origin UI integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production via ENV vars
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    """
    Middleware to inject request chronometry, acting as an internal APM.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f} sec"
    return response

class EventPayload(BaseModel):
    trigger_type: str = Field(..., description="E.g., pr_opened, ci_failed, scheduled_infra, pagerduty, manual")
    repo: Optional[str] = Field(None, description="Repository identifier (e.g., org/repo)")
    branch: Optional[str] = Field(None, description="Target branch name")
    commit_sha: Optional[str] = Field(None, description="Git commit hash")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Arbitrary JSON payload from the webhook")

@app.get("/", tags=["Health"])
async def root_health_check():
    """
    Liveness probe. Used by Kubernetes/ALBs to verify Gateway health.
    """
    return {
        "status": "operational",
        "service": "AutoOps AI Engineer Gateway",
        "version": app.version,
        "timestamp": time.time()
    }

@app.post("/webhook", tags=["Ingestion Gateway"], status_code=202)
async def ingest_webhook_event(event: EventPayload, background_tasks: BackgroundTasks):
    """
    Asynchronous Webhook Ingestion Engine.
    Acknowledges the payload instantly and delegates processing to the LangGraph DAG Orchestrator.
    """
    event_id = str(uuid.uuid4())
    logger.info(f"[{event_id}] INGEST: Event '{event.trigger_type}' intercepted for repository '{event.repo}'.")
    
    # Offload the heavy cognitive orchestration to the background job pool
    background_tasks.add_task(run_devops_workflow, event_id, event.model_dump())
    
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "event_id": event_id,
            "trigger": event.trigger_type,
            "message": "Telemetry queued for Cognitive Agent Swarm analysis.",
        }
    )

if __name__ == "__main__":
    banner = r"""
  ___               ___          ___  ___ 
 | . \ ___  _ _  ___| . \ ___  _ | . |/ __>
 | | |/ ._>| | |/ . \ | |/ . \| || | |\__ \
 |___/\___.|__/ \___/___/\___/|_|`___'<___/
                                          
    :: Autonomous DevOps Engineering ::
    """
    print(banner)
    logger.info("Bootstrapping Uvicorn ASGI Server on 0.0.0.0:8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="warning")
