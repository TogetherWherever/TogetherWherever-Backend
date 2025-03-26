from datetime import datetime
from typing import List, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RecentlyView, Trips, Activities, TripDays
from app.routers.planning_details import get_trip_photo

router = APIRouter(prefix="/api/recently-view", tags=["recently-view"])


@router.get("/")
async def get_recently_viewed_items(username: str, db: Session = Depends(get_db)) -> List[Dict]:
    """
    Get all items that the user has recently viewed.

    :param username: The username of the user who is requesting the data.
    :param db: The database session.
    :return: List of dictionaries containing recently viewed data.
    """
    recently_view = (
        db.query(RecentlyView)
        .filter(RecentlyView.username == username)
        .order_by(RecentlyView.view_date_time.desc())  # Get the latest viewed items first
        .limit(10)  # Fetch more than needed, then filter duplicates
        .all()
    )

    trip_ids = set()
    recently_viewed_items = []

    for item in recently_view:
        trip_id = item.view_trip_id
        if trip_id not in trip_ids and len(recently_viewed_items) < 3:
            trip = db.query(Trips).filter(Trips.trip_id == trip_id).first()
            if not trip:
                continue  # Skip if trip is missing

            trip_day_ids = db.query(TripDays.trip_day_id).filter(TripDays.trip_id == trip.trip_id).all()
            trip_day_ids = [day.trip_day_id for day in trip_day_ids]

            activities_count = db.query(Activities).filter(Activities.trip_day_id.in_(trip_day_ids)).count()

            item_data = {
                "username": item.username,
                "viewTripId": trip_id,
                "tripName": trip.trip_name,
                "startDate": trip.start_date,
                "endDate": trip.end_date,
                "destinationsNumber": activities_count,
                "photo": await get_trip_photo(trip.dest_id),
                "viewDateTime": item.view_date_time
            }

            recently_viewed_items.append(item_data)
            trip_ids.add(trip_id)  # Use a set for faster lookups

    return recently_viewed_items


@router.post("/")
async def add_recently_viewed_item(username: str, view_trip_id: int, db: Session = Depends(get_db)) -> Dict:
    """
    Add a new item to the recently viewed list.

    :param username: The username of the user who is requesting the data.
    :param view_trip_id: The ID of the trip that the user has viewed.
    :param db: The database session.
    :return: Dictionary containing the recently viewed data.
    """
    recently_view = RecentlyView(
        username=username,
        view_trip_id=view_trip_id,
        view_date_time=datetime.now()
    )
    db.add(recently_view)
    db.commit()

    return {"username": username, "viewTripId": view_trip_id}
