from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/get-users-data", tags=["users-data"])


@router.get("/")
async def get_user_data(db: Session = Depends(get_db)) -> List[Dict]:
    """
    Get all user data in the database.

    :param db: Database session.
    :return: List of dictionaries containing user data.
    """
    users = db.query(User).all()

    user_data = [
        {
            "userId": user.user_id,
            "name": user.username,
            "profileImage": "Not yet implemented"
        }
        for user in users
    ]

    return user_data
