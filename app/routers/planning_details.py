import json
import os
from typing import List, Dict

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trips, TripDays, RecommendedPlaces, VoteScores, Activities
from app.routers.discover import get_photo, get_place_details, open_hours_format

router = APIRouter(prefix="/api/planning-details", tags=["planning-details"])

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


async def get_trip_photo(dest_id: str) -> str:
    """
    Get the photo of the destination.

    :param dest_id: The ID of the destination.
    :return: The photo of the destination.
    """
    g_fields = "id,photos"
    response = await get_place_details(dest_id, g_fields)

    photo_names = [photo["name"] for photo in response.get("photos", [])]

    photo = await get_photo(photo_names[0], "800", "800") if photo_names else ""

    return photo


def get_number_of_votes(trip_day_id: int, members: List, db: Session) -> int:
    """
    Get the number of votes for a trip day.

    :param trip_day_id: The ID of the trip day.
    :param members: The list of members in the trip.
    :param db: Database session.
    :return: The number of votes for the trip day.
    """
    place = db.query(RecommendedPlaces).filter(RecommendedPlaces.trip_day_id == trip_day_id).first()

    vote_count = 0

    for member in members:
        vote_status = get_user_vote_status(member, place, db)

        if vote_status:
            vote_count += 1

    return vote_count


def get_user_vote_status(username: str, place, db: Session) -> bool:
    """
    Get the vote status of a user for a trip day.

    :param username: The username of the user.
    :param place: Place details from the database.
    :param db: Database session.
    :return: The vote status of the user.
    """
    vote_score = db.query(VoteScores).filter(VoteScores.recommended_place_id == place.recommended_place_id,
                                             VoteScores.username == username).first()

    return vote_score.is_voted


async def get_destinations_details(dest_id: str) -> Dict:
    """
    Get the details of destinations.

    :param dest_id: The Google Places Destination ID.
    :return: The details of suitable destinations.
    """
    g_fields = "id,displayName,editorialSummary,photos,location,regularOpeningHours"
    response = await get_place_details(dest_id, g_fields)

    photo = ""

    if response.get("photos"):
        photo_name = response["photos"][0]["name"]
        photo = await get_photo(photo_name)

    place_details = {
        "destID": response.get("id"),
        "destName": response.get("displayName")["text"],
        "photo": photo,
        "desc": response.get("editorialSummary")["text"] if response.get("editorialSummary") else "",
        "openingHours": open_hours_format(
            response.get("regularOpeningHours")["periods"] if response.get("regularOpeningHours") else []),
        "lat": response.get("location", {}).get("latitude"),
        "lon": response.get("location", {}).get("longitude")
    }

    return place_details


async def get_activities_in_period(trip_day_id: int, period: str, db: Session) -> List:
    """

    :return:
    """
    activities = db.query(Activities).filter(Activities.trip_day_id == trip_day_id,
                                             Activities.activity_period == period).all()

    activities_details = []

    for activity in activities:
        activity_details = await get_destinations_details(str(activity.activity_dest_id))
        activities_details += [activity_details]

    return activities_details


async def get_activities_details(trip_day_id: int, db: Session) -> Dict:
    """

    :return:
    """
    voted_dest = {
        "morning": await get_activities_in_period(trip_day_id, "morning", db),
        "afternoon": await get_activities_in_period(trip_day_id, "afternoon", db),
        "night": await get_activities_in_period(trip_day_id, "night", db)
    }

    return voted_dest


async def get_distance(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> Dict:
    """

    :return:
    """
    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"

    payload = json.dumps({
        "origins": [
            {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": from_lat,
                            "longitude": from_lon
                        }
                    }
                },
                "routeModifiers": {
                    "avoid_ferries": True
                }
            },
            {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": from_lat,
                            "longitude": from_lon
                        }
                    }
                },
                "routeModifiers": {
                    "avoid_ferries": True
                }
            }
        ],
        "destinations": [
            {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": to_lat,
                            "longitude": to_lon
                        }
                    }
                }
            },
            {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": to_lat,
                            "longitude": to_lon
                        }
                    }
                }
            }
        ],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE"
    })
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY,
        'X-Goog-FieldMask': 'originIndex,destinationIndex,duration,distanceMeters'
    }

    res = requests.request("POST", url, headers=headers, data=payload)

    try:
        response = res.json()
    except requests.exceptions.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from Google Routes API")

    return response


async def get_distance_details(trip_day_id: int, db: Session) -> List:
    """

    :return:
    """
    activities = db.query(Activities).filter(Activities.trip_day_id == trip_day_id).all()

    distance = []

    for number in range(1, len(activities)):
        from_activity = db.query(Activities).filter(Activities.trip_day_id == trip_day_id, Activities.activity_number == number).first()
        to_activity = db.query(Activities).filter(Activities.trip_day_id == trip_day_id, Activities.activity_number == number + 1).first()

        from_lat = from_activity.activity_dest_lat
        from_lon = from_activity.activity_dest_lon

        to_lat = to_activity.activity_dest_lat
        to_lon = to_activity.activity_dest_lon

        dist = await get_distance(from_lat, from_lon, to_lat, to_lon)

        duration = dist[0].get("duration")
        duration = int(duration[:-1]) / 60

        distance += [{
            "from": from_activity.activity_dest_name,
            "fromID": from_activity.activity_dest_id,
            "to": to_activity.activity_dest_name,
            "toID": to_activity.activity_dest_id,
            "distance_km": dist[0].get("distanceMeters") / 1000,
            "duration_min": duration
        }]

    return distance


async def get_suitable_dest_list(trip_day_id: int, db: Session) -> List:
    """
    Get the list of suitable destinations for a trip day.

    :param trip_day_id: The ID of the trip day.
    :param db: Database session.
    :return: The list of suitable destinations.
    """
    places = db.query(RecommendedPlaces).filter(RecommendedPlaces.trip_day_id == trip_day_id).all()

    suitable_dests = []

    for place in places:
        dest_details = await get_destinations_details(str(place.dest_id))
        suitable_dests.append(dest_details)

    return suitable_dests


async def get_trip_day_details(trip_day_id: int, username: str, db: Session):
    """
    Get the details of a trip day.

    :param trip_day_id: The ID of the trip day.
    :param username: The username of the user who is viewing the details.
    :param db: Database session.
    :return: The details of the trip day.
    """
    trip_day = db.query(TripDays).filter(TripDays.trip_day_id == trip_day_id).first()

    place = db.query(RecommendedPlaces).filter(RecommendedPlaces.trip_day_id == trip_day_id).first()

    trip = db.query(Trips).filter(Trips.trip_id == trip_day.trip_id).first()
    members = trip.companion.split(",") if trip.companion else []
    members += [trip.owner]

    trip_day_details = {}

    # if status == "pending" return {"day": day_number, "status": "pending"}
    if trip_day.vote_status == "pending":
        trip_day_details = {"day": trip_day.day_number, "status": "pending"}

    # if status == "voting" return the voting details
    if trip_day.vote_status == "voting":
        trip_day_details = {
            "day": trip_day.day_number,
            "status": "voting",
            "members_voted": get_number_of_votes(trip_day_id, members, db),
            "total_members": len(members),
            "user_voted": get_user_vote_status(username, place, db),
            "suitableDests": await get_suitable_dest_list(trip_day_id, db)
        }

    # if status == "complete" return the complete details
    if trip_day.vote_status == "complete":
        trip_day_details = {
            "day": trip_day.day_number,
            "status": "complete",
            "voted_dests": await get_activities_details(trip_day_id, db),
            "distance": await get_distance_details(trip_day_id, db),
        }

    return trip_day_details


@router.get("/")
async def get_planing_details(trip_id: int, username: str, db: Session = Depends(get_db)) -> Dict:
    """
    Get planning details for a trip.

    :param trip_id: The ID of the trip.
    :param username: The username of the user who is viewing the details.
    :param db: The database session.
    :return: The planning details for the trip.
    """
    trip = db.query(Trips).filter(Trips.trip_id == trip_id).first()

    members = trip.companion.split(",") if trip.companion else []
    members += [trip.owner]

    if username not in members:
        return {"message": "You are not authorized to view this trip."}

    trip_days = db.query(TripDays).filter(TripDays.trip_id == trip_id).all()

    trip_details = {
        "tripName": trip.trip_name,
        "startDate": trip.start_date,
        "lastDate": trip.end_date,
        "photo": await get_trip_photo(trip.dest_id),
        "lat": trip.dest_lat,
        "lon": trip.dest_lon,
        "companion": [
            {
                "username": user,
                "profilePic": "not yet implemented"
            }
            for user in members
        ],
        "trip_day": [
            await get_trip_day_details(int(str(trip_day.trip_day_id)), username, db)
            for trip_day in trip_days
        ]
    }

    return trip_details
