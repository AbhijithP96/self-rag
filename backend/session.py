from pydantic import BaseModel
from typing import Dict, Optional, Any

import redis
import uuid

from logging_config import logger

r = redis.Redis(host='redis', port=6379, decode_responses=True)

def get_redis_obj():
    return r

class Session(BaseModel):
    """Pydantic model for managing user session data and files.
    
    Stores session ID, API key, and references to uploaded PDF files in MongoDB.
    Session data is persisted in Redis with a 30-minute expiration.
    """
    session_id: str
    model : Optional[str] = None
    api_key: Optional[str] = None
    mongo_files: Dict[str, Any] = {}

    @classmethod
    def create_new(cls):
        """Create a new session with a unique ID.
        
        Returns:
            Session: New session instance with generated UUID
        """
        session_id = str(uuid.uuid4())
        logger.debug(f"Creating new session with ID: {session_id}")
        return cls(session_id=session_id)

    def save(self):
        """Persist session data to Redis with 30-minute expiration."""
        try:
            r.setex(f"session:{self.session_id}", 1800, self.model_dump_json())
            logger.debug(f"Session {self.session_id} saved to Redis with 30-min expiration")
        except Exception as e:
            logger.error(f"Failed to save session {self.session_id}: {str(e)}", exc_info=True)
            raise

    @classmethod
    def load(cls, session_id):
        """Load session from Redis.
        
        Args:
            session_id: Session identifier to retrieve
            
        Returns:
            Session: Loaded session object or None if not found
        """
        try:
            data = r.get(f"session:{session_id}")
            if not data:
                logger.warning(f"Session {session_id} not found in Redis")
                return None
            logger.debug(f"Session {session_id} loaded from Redis")
            return cls.model_validate_json(data)
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {str(e)}", exc_info=True)
            return None