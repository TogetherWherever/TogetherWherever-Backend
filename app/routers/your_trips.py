from typing import List, Dict

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trips, TripDays, Activities, User
from app.routers.planning_details import get_trip_photo

router = APIRouter(prefix="/api/your-trips", tags=["your-trips"])


@router.get("/")
async def get_your_trips(username: str, db: Session = Depends(get_db)) -> List[Dict]:
    """
    Get all trips that the user is in the members list.

    :param username: The username of the user who is requesting the data.
    :param db: The database session.
    :return: The user's trips or a message if the user is not found.
    """
    user_exit = db.query(User).filter(User.username == username).all()

    if not user_exit:
        raise HTTPException(status_code=404, detail=f"Invalid username: {username}")

    trips = db.query(Trips).filter((Trips.owner == username) | Trips.companion.contains(username)).all()

    your_trips = []

    for trip in trips:
        trip_day_ids = db.query(TripDays.trip_day_id).filter(TripDays.trip_id == trip.trip_id).all()
        trip_day_ids = [day.trip_day_id for day in trip_day_ids]

        activities_count = db.query(Activities).filter(Activities.trip_day_id.in_(trip_day_ids)).count()

        your_trips.append({
            "tripId": trip.trip_id,
            "tripName": trip.trip_name,
            "startDate": trip.start_date,
            "endDate": trip.end_date,
            "destinationsNumber": activities_count,
            "owner": trip.owner,
            "photo": await get_trip_photo(trip.dest_id)
        })

    return your_trips
