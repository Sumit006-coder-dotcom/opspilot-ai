"""Compatibility dependency names used by existing endpoint modules."""
from api.auth import current_user, require_roles
from fastapi import Depends

def require_auth(user=Depends(current_user)):
    return user
