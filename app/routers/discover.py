import asyncio
import os
import requests
import json
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/discover-place-details", tags=["discover"])

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


async def get_photo(photo_name: str) -> str:
    """
    Get a single photo from Google Places API (Place Photo).
    :param photo_name: Photo name
    :return: Photo URL
    """
    headers = {'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY}
    url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=300&maxWidthPx=300"
    res = requests.get(url, headers=headers, allow_redirects=False)

    if res.status_code == 302:  # Google redirects to actual image
        return res.headers["Location"]
    else:
        print(f"Error fetching photo: {res.text}")  # Debugging
        return None


async def get_nearby_places(lat: float, lon: float) -> List[Dict]:
    """
    Get nearby places from Google Places API (Nearby Search).
    :param lat: Latitude
    :param lon: Longitude
    :return: List of nearby places
    """
    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = json.dumps({
        "maxResultCount": 8,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lon
                },
                "radius": 5000  # Set radius to 5 km
            }
        }
    })
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY,
        'X-Goog-FieldMask': 'places.id,places.displayName,places.photos'  # Optimized field mask
    }
    res = requests.request("POST", url, headers=headers, data=payload)
    try:
        response = res.json()
    except requests.exceptions.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from Google Places API")

    nearby_places = []
    for place in response.get("places", []):
        photo = None
        if place.get("photos"):
            photo_name = place["photos"][0]["name"]
            photo = await get_photo(photo_name)

        place_data = {
            "destID": place.get("id"),
            "destName": place.get("displayName")["text"],
            "photos": photo if photo else ""
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
    url = f"https://places.googleapis.com/v1/places/{dest_id}?fields=id,displayName,types,editorialSummary,rating,formattedAddress,internationalPhoneNumber,goodForChildren,accessibilityOptions,photos,location"
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

    # Fetch photos and nearby places concurrently
    photo_names = [photo["name"] for photo in response.get("photos", [])]
    lat = response.get("location", {}).get("latitude")
    lon = response.get("location", {}).get("longitude")

    photos, nearby_places = await asyncio.gather(
        asyncio.gather(*(get_photo(photo_name) for photo_name in photo_names)) if photo_names else [],
        get_nearby_places(lat, lon) if lat and lon else []
    )

    return {
        "destID": dest_id,
        "destName": response.get("displayName")["text"],
        "destType": response.get("types"),
        "desc": response.get("editorialSummary")["text"] if response.get("editorialSummary") else "",
        "rating": response.get("rating"),
        "address": response.get("formattedAddress"),
        "phoneNum": response.get("internationalPhoneNumber"),
        "fac": {
            "goodForChildren": response.get("goodForChildren"),
            "accessibility": response.get("accessibilityOptions"),
        },
        "photos": photos,
        "lat": lat,
        "lon": lon,
        "nearbyPlaces": nearby_places
    }
