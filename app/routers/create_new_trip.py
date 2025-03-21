from datetime import timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trips, TripDays
from app.schemas import CreateNewTrip

from app.routers.recommendation_model import get_travel_group_preferences, one_hot_encode_preferences, \
    extract_group_profile, get_suitable_destinations, get_recommendations, get_nearby_destinations_from_api

router = APIRouter(prefix="/api/create-new-trip", tags=["create-new-trip"])


def create_recommendations(trip_id: int, trip: CreateNewTrip,  db: Session) -> pd.DataFrame:
    """
    Create recommendations for a trip.

    :param trip_id: The ID of the trip.
    :param trip: The trip details.
    :param db: Database session.
    """
    # Get the travel group preferences
    travel_group_preferences = get_travel_group_preferences(trip_id, db)

    # Get nearby destinations from Google Places API
    nearby_places = get_nearby_destinations_from_api(trip.dest_lat, trip.dest_lon)

    # Get recommendations
    recommendations = get_recommendations(travel_group_preferences, nearby_places)

    return recommendations


@router.post('/')
async def create_new_trip(trip: CreateNewTrip, db: Session = Depends(get_db)):
    """
    Create a new trip and store it in the database.
    """
    # Validate date range
    if trip.start_date > trip.end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    try:
        # Create a new trip record
        new_trip = Trips(
            owner=trip.owner,
            trip_name=trip.trip_name,
            dest_id=trip.dest_id,
            dest_name=trip.dest_name,
            start_date=trip.start_date,
            end_date=trip.end_date,
            duration=trip.duration,
            companion=trip.companion  # Comma-separated string of companion IDs
        )

        db.add(new_trip)
        db.commit()
        db.refresh(new_trip)

        # Create trip days
        for day in range(trip.duration):
            new_trip_day = TripDays(
                trip_id=new_trip.trip_id,
                day_number=day + 1,
                date=trip.start_date + timedelta(days=day + 1)
            )

            db.add(new_trip_day)
            db.commit()
            db.refresh(new_trip_day)

        # Create recommendations
        recommendations = create_recommendations(new_trip.trip_id, trip, db)

        print(recommendations.to_dict())

        return {"message": "Trip created successfully", "trip_id": new_trip.trip_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating trip: {str(e)}")
