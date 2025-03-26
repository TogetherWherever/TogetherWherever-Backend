from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/user-profile", tags=["user-profile"])


@router.get("/")
async def get_user_profile(username: str, db: Session = Depends(get_db)) -> Dict:
    """
    Get the user's profile information.

    :param username: The username of the user who is requesting the data.
    :param db: The database session.
    :return: The user's profile information.
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=404, detail=f"Invalid username: {username}")

    preferences = user.preferences.split(",") if user.preferences else []

    result = {
        "username": user.username,
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "preferences": preferences
    }

    return result
