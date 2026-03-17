from fastapi import APIRouter, HTTPException, status, Depends, Header
from app.models.schemas import Digest
from app.utils.storage import read_json_file, write_json_file
from app.scrapers.monitor import JournalMonitor
from typing import List, Optional

router = APIRouter()

DIGESTS_FILE = "digests.json"


def get_current_user_id(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Extract user ID from JWT token if provided (optional authentication).
    
    Args:
        authorization: Optional Authorization header with Bearer token
        
    Returns:
        User ID from token or None if not authenticated
    """
    if not authorization:
        return None
    
    try:
        from app.utils.security import decode_access_token
        from app.utils.storage import read_json_file as read_users
        
        # Extract token from "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        token = parts[1]
        payload = decode_access_token(token)
        
        if not payload:
            return None
        
        # Get user email from token
        email = payload.get("sub")
        if not email:
            return None
        
        # Look up user ID
        users = read_users("users.json")
        if email not in users:
            return None
        
        return users[email]["id"]
    except Exception:
        return None


@router.post("/generate")
def generate_digest(user_id: Optional[str] = Depends(get_current_user_id)):
    """
    Generate a new digest by monitoring journals.
    If authenticated, applies personalized relevance filtering.
    """
    monitor = JournalMonitor()
    digest = monitor.generate_digest(user_id=user_id)
    
    if not digest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No papers found. Please add journals first."
        )
    
    return digest

@router.get("/latest", response_model=Digest)
def get_latest_digest():
    digests = read_json_file(DIGESTS_FILE)
    
    if not digests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No digests found"
        )
    
    # Get the most recent digest
    digest_list = list(digests.values())
    latest = max(digest_list, key=lambda x: x["generatedAt"])
    
    return latest

@router.get("", response_model=List[Digest])
def get_digests():
    digests = read_json_file(DIGESTS_FILE)
    digest_list = list(digests.values())
    
    # Sort by date, newest first
    digest_list.sort(key=lambda x: x["generatedAt"], reverse=True)
    
    return digest_list

@router.get("/{digest_id}", response_model=Digest)
def get_digest(digest_id: str):
    digests = read_json_file(DIGESTS_FILE)
    
    if digest_id not in digests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Digest not found"
        )
    
    return digests[digest_id]
