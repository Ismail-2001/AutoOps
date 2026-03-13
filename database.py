import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any, Dict

from sqlmodel import Field, SQLModel, create_engine, Session

logger = logging.getLogger("AutoOps.Database")

class AuditLog(SQLModel, table=True):
    """
    Immutable cryptographic-style ledger for all autonomous agent actions.
    Ensures SOC2 compliance and transparency for the AI Swarm.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(index=True, description="Unique uuid telemetry marker")
    trigger_type: str = Field(description="Webhook or cron trigger identity")
    repo: Optional[str] = Field(default=None, description="Affected repository")
    agent_invoked: str = Field(description="The primary CrewAI agent executed")
    action_taken: str = Field(description="Synopsis of the action taken")
    confidence: float = Field(default=0.0, description="LLM heuristic confidence score")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Strict UTC timestamp of the ledger entry"
    )
    payload_dump: str = Field(default="{}", description="Stringified JSON of raw tool payloads")

# Determine optimal dialect (PostgreSQL for production, SQLite for local dev)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auto_ops.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure highly available connection pooling if using PostgreSQL
engine_args: Dict[str, Any] = {"echo": False}
if "postgresql" in DATABASE_URL:
    engine_args.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800  # Recycle idle connections after 30 mins
    })

engine = create_engine(DATABASE_URL, **engine_args)

def create_db_and_tables():
    """
    Idempotent DDL migration execution. 
    Synchronizes SQLModel domain models to physical tables.
    """
    try:
        SQLModel.metadata.create_all(engine)
        logger.info(f"Database schema verified/created successfully at [{DATABASE_URL.split('@')[-1]}]")
    except Exception as e:
        logger.error(f"FATAL: Database schema unresolvable. Connectivity issue: {str(e)}")
        raise

def log_audit_trail(event_id: str, trigger_type: str, repo: str, agent_invoked: str, 
                    action: str, confidence: float, payload: dict):
    """
    Persists an immutable record of an AI agent's execution sequence. 
    Crucial for post-incident reviews (PIRs) and root cause analysis.
    """
    new_log = AuditLog(
        event_id=event_id,
        trigger_type=trigger_type,
        repo=repo if repo else "unknown",
        agent_invoked=agent_invoked,
        action_taken=action,
        confidence=confidence,
        payload_dump=json.dumps(payload)
    )
    
    try:
        with Session(engine) as session:
            session.add(new_log)
            session.commit()
            logger.debug(f"Audit log committed - EventID: {event_id}")
    except Exception as e:
        # We catch and log, rather than halting the system for telemetry failure
        logger.error(f"Dropping audit telemetry for {event_id} due to persistence fault: {str(e)}")
