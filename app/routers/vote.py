from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TripDays, Trips
from app.routers.planning_details import get_planing_details, get_number_of_votes
from app.routers.recommendation_model import get_members
from app.schemas import PatchVoteScore

router = APIRouter(prefix="/api/vote", tags=["vote"])


def update_vote_status(trip_id: int, trip_day_id: int, db: Session):
    """
    Update the vote status for a trip day.

    :param trip_id: The ID of the trip.
    :param trip_day_id: The ID of the trip day.
    :param db: The database session.
    """
    members = get_members(trip_id, db)
    vote_counts = get_number_of_votes(trip_day_id, members, db)
    total_members = len(members)

    if vote_counts == total_members:
        trip_day = db.query(TripDays).filter(TripDays.trip_day_id == trip_day_id).first()
        trip_day.vote_status = "complete"
        db.commit()
        db.refresh(trip_day)


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


@router.patch("/submit-vote")
async def update_vote_score(vote_score: PatchVoteScore, db: Session = Depends(get_db)) -> Dict:
    """
    Submit and update the vote score for a trip day.

    :param vote_score: The vote score details.
    :param db: The database session.
    :return: The message indicating the success of the operation.
    """
    trip_day = db.query(TripDays).filter(TripDays.trip_id == vote_score.trip_id,
                                         TripDays.day_number == vote_score.trip_day_number).first()

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
                    "trip_day_id": trip_day.trip_day_id,
                    "dest_id": dest_id,
                    "username": vote_score.voted_person
                }
            )

        db.commit()

        update_vote_status(vote_score.trip_id, int(str(trip_day.trip_day_id)), db)

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
