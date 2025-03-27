from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Trips

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

    trips_count = db.query(Trips).filter((Trips.owner == username) | Trips.companion.contains(username)).count()

    result = {
        "username": user.username,
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "preferences": preferences,
        "tripsCount": trips_count
    }

    return result


@router.patch("/update-preferences")
async def update_user_preferences(username: str, preferences: list, db: Session = Depends(get_db)) -> Dict:
    """
    Update the user's preferences.

    :param username: The username of the user who is updating the preferences.
    :param preferences: The list of preferences to update.
    :param db: The database session.
    :return: The updated user's preferences.
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=404, detail=f"Invalid username: {username}")

    # Convert list to comma-separated string
    user.preferences = ",".join(preferences) if preferences else None

    db.commit()

    return {"message": "User preferences updated successfully"}
