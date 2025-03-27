from datetime import timedelta, date
from typing import List, Dict

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trips, TripDays, RecommendedPlaces, VoteScores
from app.routers.discover import get_place_details, open_hours_format
from app.routers.recommendation_model import get_travel_group_preferences, get_recommendations, \
    get_nearby_destinations, get_members
from app.schemas import CreateNewTrip

router = APIRouter(prefix="/api/create-new-trip", tags=["create-new-trip"])


async def create_recommendations(trip_id: int, lat: float, lon: float, db: Session,
                                 previous_dest: List = None) -> pd.DataFrame:
    """
    Create recommendations for a trip.

    :param trip_id: The ID of the trip.
    :param lat: The latitude of the destination.
    :param lon: The longitude of the destination.
    :param db: Database session.
    :param previous_dest: The previous destinations from the previous day.
    :return: The recommendations.
    """
    # Get the travel group preferences
    travel_group_preferences = get_travel_group_preferences(trip_id, db)

    # Get nearby destinations from Google Places API
    nearby_places = await get_nearby_destinations(lat, lon)

    if previous_dest:
        nearby_places = nearby_places[~nearby_places["AttractionId"].isin(previous_dest)]

    # Get recommendations
    recommendations = get_recommendations(travel_group_preferences, nearby_places)

    return recommendations


def creat_new_trip_record(trip: CreateNewTrip, db: Session):
    """
    Create a new trip record in the database.

    :param trip: The trip details.
    :param db: Database session.
    """
    # Create a new trip record
    new_trip = Trips(
        owner=trip.owner,
        trip_name=trip.trip_name,
        dest_id=trip.dest_id,
        dest_name=trip.dest_name,
        dest_lat=trip.dest_lat,
        dest_lon=trip.dest_lon,
        start_date=trip.start_date,
        end_date=trip.end_date,
        duration=trip.duration,
        companion=trip.companion  # Comma-separated string of companion IDs
    )

    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)

    # Create trip days records
    for day in range(trip.duration):
        new_trip_day = TripDays(
            trip_id=new_trip.trip_id,
            day_number=day + 1,
            date=trip.start_date + timedelta(days=day + 1),
            vote_status="pending"
        )

        db.add(new_trip_day)
        db.commit()
        db.refresh(new_trip_day)

    return new_trip


async def check_open_time(dest_id: str, trip_day_date: date, opening_hours: List[Dict] = None) -> bool:
    """
    Check if the destination is open at the given trip date.

    :param dest_id: The destination ID.
    :param trip_day_date: The date of the trip day.
    :param opening_hours: The opening hours of the destination.
    :return: True if the destination is open, False otherwise.
    """
    if opening_hours is None:
        g_field = "regularOpeningHours"
        response = await get_place_details(dest_id, g_field)

        # Check if opening hours exist
        opening_hours = response.get("regularOpeningHours")["periods"] if response.get("regularOpeningHours") else []

    # Get the current day of the week
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    day_name = day_names[trip_day_date.weekday()]

    # Process opening hours
    format_hour = open_hours_format(opening_hours)

    # Check if the destination has open hours on this day
    return day_name in format_hour


async def create_recommendations_record(trip_id: int, recommendations: pd.DataFrame, db: Session, day_number: int = 1):
    """
    Create a new recommendations record in the database.

    :param trip_id: The ID of the trip.
    :param recommendations: The recommendations.
    :param db: Database session.
    :param day_number: The day number for which the recommendations are created.
    """
    trip_day = db.query(TripDays).filter(TripDays.trip_id == trip_id, TripDays.day_number == day_number).first()

    members = get_members(trip_id, db)

    records_count = 0

    for idx, row in recommendations.iterrows():
        is_open = await check_open_time(row["AttractionId"], trip_day.date)

        if is_open:
            new_recommendation = RecommendedPlaces(
                trip_id=trip_id,
                trip_day_id=trip_day.trip_day_id,
                dest_id=row["AttractionId"],
                dest_name=row["Attraction"],
            )

            db.add(new_recommendation)
            db.commit()
            db.refresh(new_recommendation)

            create_vote_scores_records(new_recommendation.recommended_place_id, members, db)

            records_count += 1

        if records_count >= 6:
            break

    # change the vote status to voting
    trip_day.vote_status = "voting"
    db.commit()
    db.refresh(trip_day)


def create_vote_scores_records(recommended_place_id: int, members: List[str], db: Session):
    """
    Create a new vote scores record in the database.

    :param recommended_place_id: The ID of the recommended place.
    :param members: The list of members in the travel group.
    :param db: Database session.
    """
    for member in members:
        new_vote_score = VoteScores(
            recommended_place_id=recommended_place_id,
            username=member,
        )

        db.add(new_vote_score)
        db.commit()
        db.refresh(new_vote_score)


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
        new_trip = creat_new_trip_record(trip, db)

        # Create recommendations
        recommendations = await create_recommendations(new_trip.trip_id, new_trip.dest_lat, new_trip.dest_lon, db)

        # Create recommendations record
        await create_recommendations_record(new_trip.trip_id, recommendations, db)

        return {
            "message": "Trip created successfully",
            "trip_id": new_trip.trip_id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating trip: {str(e)}")
