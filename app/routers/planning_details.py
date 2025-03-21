import os

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trips, TripDays
from app.routers.discover import get_photo

router = APIRouter(prefix="/api/planning-details", tags=["planning-details"])

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


async def get_trip_photo(dest_id: str) -> str:
    """
    Get the photo of the destination.

    :param dest_id: The ID of the destination.
    :return: The photo of the destination.
    """
    url = f"https://places.googleapis.com/v1/places/{dest_id}?fields=id,photos"
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY
    }
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail=f"Google Places API error: {res.text}")

    try:
        response = res.json()
    except requests.exceptions.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from Google Places API")

    photo_names = [photo["name"] for photo in response.get("photos", [])]

    photo = await get_photo(photo_names[0]) if photo_names else ""

    return photo


@router.get("/")
async def get_planing_details(trip_id: int, username: str, db: Session = Depends(get_db)):
    """
    Get planning details for a trip.

    :param trip_id:
    :param username:
    :param db:
    :return:
    """
    trip = db.query(Trips).filter(Trips.trip_id == trip_id).first()

    if trip.owner != username and username not in trip.companion.split(","):
        return {"message": "You are not authorized to view this trip."}

    trip_days = db.query(TripDays).filter(TripDays.trip_id == trip_id).all()

    trip_details = {
        "tripName": trip.trip_name,
        "startDate": trip.start_date,
        "lastDate": trip.end_date,
        "photo": await get_trip_photo(trip.dest_id),
        "lat": trip.dest_lat,
        "lon": trip.dest_lon,
        "companion": trip.companion.split(","),
        "trip_day": [
            {
                "day": trip_days[0].day_number,
                "status": "voting",
                "voted": False,
                "members_voted": 0,
                "total_members": 6,
                "user_voted": False,
                "suitableDests": [
                    {
                        "destID": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                        "destName": "Eiffel Tower",
                        "photos": "https://www.gstatic.com/webp/gallery/1.jpg"
                    }
                ]
            }
        ]
    }

    return {"message": "Hello, World!"}
