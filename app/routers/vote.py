from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TripDays, Trips
from app.routers.planning_details import get_planing_details

router = APIRouter(prefix="/api/vote", tags=["vote"])


@router.get("/vote-details")
async def get_destinations_details_for_vote(trip_id: int, day_number: int, username: str, db: Session = Depends(get_db)):
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
