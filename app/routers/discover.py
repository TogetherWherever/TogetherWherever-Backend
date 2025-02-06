import os
import requests
import json
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/discover-place-details", tags=["discover"])

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


async def get_photos(photo_names: List[str]) -> List[str]:
    """
    Get photos from Google Places API (Place Photo).

    :param photo_names: List of photo names
    :return: List of photo URLs
    """
    photos = []
    headers = {'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY}

    for photo_name in photo_names:
        url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=500"

        res = requests.get(url, headers=headers, allow_redirects=False)

        if res.status_code == 302:  # Google redirects to actual image
            photos.append(res.headers["Location"])
        else:
            print(f"Error fetching photo: {res.text}")  # Debugging

    return photos


async def get_nearby_places(lat: float, lon: float) -> List[Dict]:
    """
    Get nearby places from Google Places API (Nearby Search).

    :param lat: Latitude
    :param lon: Longitude
    :return: List of nearby places
    """
    url = "https://places.googleapis.com/v1/places:searchNearby"

    payload = json.dumps({
        "maxResultCount": 15,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lon
                },
                "radius": 10000 # 10 km
            }
        }
    })

    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY,
        'X-Goog-FieldMask': 'places.id,places.displayName,places.rating,places.photos'
    }

    res = requests.request("POST", url, headers=headers, data=payload)

    try:
        response = res.json()
    except requests.exceptions.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from Google Places API")

    nearby_places = []

    for place in response.get("places", []):
        # Get photos
        photo_names = [place.get("photos", [])[0]["name"]] if place.get("photos") else []
        photos = await get_photos(photo_names) if photo_names else []

        place_data = {
            "destID": place.get("id"),
            "destName": place.get("displayName")["text"],
            "rating": place.get("rating"),
            "photos": photos[0]
        }

        nearby_places.append(place_data)

    return nearby_places


@router.get("/")
async def discover_place_details(dest_id: str = Query(..., min_length=1)) -> Dict:
    """
    Fetch place details from Google Places API (Place Details).

    :param dest_id: Google Places Destination ID
    :return: Place details
    """
    url = f"https://places.googleapis.com/v1/places/{dest_id}"
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY,
        'X-Goog-FieldMask': '*'  # Fetch all fields
    }

    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail=f"Google Places API error: {res.text}")

    try:
        response = res.json()
    except requests.exceptions.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from Google Places API")

    # Get photos
    photo_names = [photo["name"] for photo in response.get("photos", [])]
    photos = await get_photos(photo_names) if photo_names else []

    # Get nearby places
    lat = response.get("location", {}).get("latitude")
    lon = response.get("location", {}).get("longitude")
    nearby_places = await get_nearby_places(lat, lon) if lat and lon else []

    return {
        "destID": dest_id,
        "destName": response.get("displayName")["text"],
        "destType": response.get("types"),
        "desc": response.get("editorialSummary"),
        "rating": response.get("rating"),
        "address": response.get("formattedAddress"),
        "phoneNum": response.get("internationalPhoneNumber"),
        # "openHr": response.get("regularOpeningHours"),
        "fac": {
            "goodForChildren": response.get("goodForChildren"),
            "accessibility": response.get("accessibilityOptions"),
        },
        "photos": photos,
        "lat": lat,
        "lon": lon,
        "nearbyPlaces": nearby_places
    }
