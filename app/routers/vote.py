from datetime import date
from typing import Dict, List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TripDays, Trips, Activities
from app.routers.create_new_trip import create_recommendations, create_recommendations_record
from app.routers.discover import get_place_details, open_hours_format
from app.routers.planning_details import get_planing_details, get_number_of_votes
from app.routers.recommendation_model import get_members, get_best_destinations, get_travel_group_preferences, \
    get_nearby_destinations, get_recommendations
from app.schemas import PatchVoteScore

router = APIRouter(prefix="/api/vote", tags=["vote"])


def update_vote_status(trip_id: int, trip_day_id: int, db: Session) -> str:
    """
    Update the vote status for a trip day.

    :param trip_id: The ID of the trip.
    :param trip_day_id: The ID of the trip day.
    :param db: The database session.
    :return: The updated vote status.
    """
    members = get_members(trip_id, db)
    vote_counts = get_number_of_votes(trip_day_id, members, db)
    total_members = len(members)

    trip_day = db.query(TripDays).filter(TripDays.trip_day_id == trip_day_id).first()

    if vote_counts == total_members:
        trip_day.vote_status = "complete"
        db.commit()
        db.refresh(trip_day)

    return trip_day.vote_status


def get_period(opening_hours: Dict[str, Dict[str, str]], act_date: date) -> str:
    """
    Get the period of the day based on the opening hours of the destination.

    :param opening_hours: The opening hours of the destination.
    :param act_date: The date of the day.
    :return: The period of the day (morning, afternoon, night).
    """
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    day_name = day_names[act_date.weekday()]

    # Check if the destination is open in the morning, afternoon, or night
    if opening_hours[day_name]["open"] < "12:00" < opening_hours[day_name]["close"]:
        period = "morning"
    elif "12:00" < opening_hours[day_name]["open"] < "18:00" < opening_hours[day_name]["close"]:
        period = "afternoon"
    else:
        period = "night"

    return period


async def create_activities_record(trip_id: int, day_number: int, dest_id_lst: List[str], db: Session):
    """
    Create activities record for a day.

    :param trip_id: The unique identifier of the trip.
    :param day_number: The day number of the trip.
    :param dest_id_lst: The list of destination IDs.
    :param db: The database session.
    :return:
    """
    trip_day = db.query(TripDays).filter(TripDays.trip_id == trip_id, TripDays.day_number == day_number).first()

    g_fields = 'id,displayName,location'

    activity_number = 1

    for dest_id in dest_id_lst:
        dest_detail = await get_place_details(dest_id, g_fields)

        new_activity = Activities(
            trip_day_id=trip_day.trip_day_id,
            activity_dest_id=dest_id,
            activity_dest_name=dest_detail.get('displayName')["text"],
            activity_dest_lat=dest_detail.get("location", {}).get("latitude"),
            activity_dest_lon=dest_detail.get("location", {}).get("longitude"),
            activity_number=activity_number,
            activity_period="morning"
        )

        db.add(new_activity)
        db.commit()

        activity_number += 1


async def create_complete_plan_after_voting(best_dest: pd.DataFrame, trip_id: int, day_number: int, db: Session):
    """
    Create a plan after voting is complete.

    :param best_dest: The best destination for the day.
    :param trip_id: The unique identifier of the trip.
    :param day_number: The day number of the trip.
    :param db: Database session.
    :return: None
    """
    best_dest_id = best_dest["AttractionId"].values[0]

    g_fields = "location"
    best_dest_detail = await get_place_details(best_dest_id, g_fields)
    lat = best_dest_detail.get("location", {}).get("latitude")
    lon = best_dest_detail.get("location", {}).get("longitude")

    nearby_places = await get_nearby_destinations(lat, lon, radius=3000)

    travel_group_preferences = get_travel_group_preferences(trip_id, db)
    suitable_destinations = get_recommendations(travel_group_preferences, nearby_places)
    suitable_destinations = suitable_destinations[suitable_destinations["AttractionId"] != best_dest_id]
    suitable_destinations = suitable_destinations.head(4)

    act_dest_lst = [best_dest_id]

    for i, dest in suitable_destinations.iterrows():
        act_dest_lst += [dest["AttractionId"]]

    await create_activities_record(trip_id, day_number, act_dest_lst, db)


async def create_next_day_recommendations(trip_id: int, day_number: int, db: Session):
    """
    Create recommendations for the next day.

    :param trip_id: The unique identifier of the trip.
    :param day_number: The day number of the trip.
    :param db: Database session.
    """
    trip = db.query(Trips).filter(Trips.trip_id == trip_id).first()
    trip_day = db.query(TripDays).filter(TripDays.trip_id == trip_id).all()

    trip_day_ids = [day.trip_day_id for day in trip_day]

    # Get all previous activity IDs
    activities = db.query(Activities).filter(Activities.trip_day_id.in_(trip_day_ids)).all()
    activities_ids = [activity.activity_dest_id for activity in activities]

    # Get the recommendations for the next day
    recommendations = await create_recommendations(trip_id, trip.dest_lat, trip.dest_lon, db, activities_ids)

    create_recommendations_record(trip_id, recommendations, db, day_number)


@router.get("/vote-details")
async def get_destinations_details_for_vote(trip_id: int, day_number: int, username: str,
                                            db: Session = Depends(get_db)):
    """
    Get all destinations details for voting.

    :param trip_id: The unique identifier of the trip.
    :param day_number: The day number of the trip.
    :param username: The username of the user who is requesting the data.
    :param db: Database session.
    :return: List of dictionaries containing destinations details.
    """
    trip = db.query(Trips).filter(Trips.trip_id == trip_id).first()

    planning_details = await get_planing_details(trip_id, username, db)

    trip_day = db.query(TripDays).filter(TripDays.trip_id == trip_id, TripDays.day_number == day_number).first()

    destinations = []
    members_voted = ""
    total_members = ""

    for day_details in planning_details["trip_day"]:
        if day_details["day"] == day_number and day_details["status"] == "voting":
            for dest in day_details["suitableDests"]:
                dest_details = {
                    "destID": dest["destID"],
                    "destName": dest["destName"],
                    "photo": dest["photo"]
                }
                destinations += [dest_details]

            members_voted = day_details["members_voted"]
            total_members = day_details["total_members"]

    vote_details = {
        "trip_id": trip.trip_id,
        "tripName": planning_details["tripName"],
        "photo": planning_details["photo"],
        "startDate": planning_details["startDate"],
        "lastDate": planning_details["lastDate"],
        "voting_date": trip_day.date,
        "members_voted": members_voted,
        "total_members": total_members,
        "companion": planning_details["companion"],
        "destinations": destinations,
    }

    return vote_details


async def get_destinations(dest_id_lst: List[str]) -> pd.DataFrame:
    g_fields = 'id,displayName,types'
    destinations = []
    for dest_id in dest_id_lst:
        place = await get_place_details(dest_id, g_fields)
        destinations.append(place)

    places_df = pd.DataFrame(
        [
            {
                "AttractionId": place.get('id'),
                "Attraction": place.get('displayName')["text"],
                "AttractionType": ",".join(place.get('types'))  # Convert list of types to comma-separated string
            }
            for place in destinations
        ]
    )

    return places_df


@router.patch("/submit-vote")
async def update_vote_score(vote_score: PatchVoteScore, db: Session = Depends(get_db)) -> Dict:
    """
    Submit and update the vote score for a trip day.

    :param vote_score: The vote score details.
    :param db: The database session.
    :return: The message indicating the success of the operation.
    """
    trip_id = vote_score.trip_id
    day_number = vote_score.trip_day_number
    trip_day = db.query(TripDays).filter(TripDays.trip_id == trip_id,
                                         TripDays.day_number == day_number).first()

    trip_day_id = trip_day.trip_day_id

    if not trip_day:
        raise HTTPException(status_code=404, detail="Trip day not found.")

    try:
        for dest_id, score in vote_score.scores.items():
            db.execute(
                text("""
                    UPDATE vote_scores vs
                    SET vote_score = :new_score, is_voted = TRUE
                    FROM recommended_places rp
                    WHERE vs.recommended_place_id = rp.recommended_place_id
                    AND rp.trip_day_id = :trip_day_id
                    AND rp.dest_id = :dest_id
                    AND vs.username = :username;
                """),
                {
                    "new_score": score,
                    "trip_day_id": trip_day_id,
                    "dest_id": dest_id,
                    "username": vote_score.voted_person
                }
            )

        db.commit()

        vote_status = update_vote_status(trip_id, trip_day_id, db)

        if vote_status == "complete":
            trip_duration = db.query(Trips).filter(Trips.trip_id == trip_id).first().duration
            # get best destination
            travel_group = get_travel_group_preferences(trip_id, db)

            destinations = await get_destinations(list(vote_score.scores.keys()))
            best_dest_df = get_best_destinations(trip_day_id, travel_group, destinations, db)

            await create_complete_plan_after_voting(best_dest_df, trip_id, day_number, db)

            if day_number < trip_duration:
                await create_next_day_recommendations(trip_id, day_number + 1, db)

        return {"message": "Vote updated successfully."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating vote: {str(e)}")


@router.get("/vote-status")
async def get_vote_status(trip_id: int, day_number: int, db: Session = Depends(get_db)) -> Dict:
    """
    Get the vote status for a trip day.

    :param trip_id: The ID of the trip.
    :param day_number: The day number of the trip.
    :param db: The database session.
    :return: The vote status for the trip day.
    """
    trip_day = db.query(TripDays).filter(TripDays.trip_id == trip_id, TripDays.day_number == day_number).first()

    return {"vote_status": trip_day.vote_status}
