# api/deps.py
import time
from collections import defaultdict
from fastapi import Depends, HTTPException
from auth.security import get_current_user
from config.settings import settings
from models.user import User

_request_counts = defaultdict(list)

async def rate_limit(user: User = Depends(get_current_user)) -> User:
    now = time.time()
    uid = str(user.id)
    window = settings.RATE_LIMIT_PERIOD
    cap = settings.RATE_LIMIT_CALLS
    _request_counts[uid] = [t for t in _request_counts[uid] if now - t < window]
    if len(_request_counts[uid]) >= cap:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _request_counts[uid].append(now)
    return user
