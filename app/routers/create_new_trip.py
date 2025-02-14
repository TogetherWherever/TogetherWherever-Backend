from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from typing import List
from datetime import date
from sqlalchemy.orm import Session
from database import get_db
from models.trips import Trips
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/create-new-trip", tags=["create-new-trip"])

class NewTrip(BaseModel):
    owner: str = Field(..., min_length=1, description="Owner of the trip")
    trip_name: str = Field(..., min_length=1, description="Trip name")
    dest_id: str = Field(..., min_length=1, description="Google Places Destination ID")
    dest_name: str = Field(..., min_length=1, description="Destination name")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    companion: List[str] = Field(default_factory=list, description="List of companions")

@router.post('/')
async def create_new_trip(trip: NewTrip, response: Response, db: Session = Depends(get_db)):
    """
    Create a new trip and store it in the database.
    """
    # Validate date range
    if trip.start_date > trip.end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    try:
        # Calculate duration
        duration = (trip.end_date - trip.start_date).days + 1

        # Create a new trip record
        new_trip = Trips(
            owner=trip.owner,
            trip_name=trip.trip_name,
            dest_id=trip.dest_id,
            dest_name=trip.dest_name,
            start_date=trip.start_date,
            end_date=trip.end_date,
            duration=duration,
            companion=",".join(trip.companion)  # Convert list to comma-separated string
        )

        db.add(new_trip)
        db.commit()
        db.refresh(new_trip)

        # Set custom headers in the response
        response.headers["X-Trip-Created"] = "true"
        response.headers["Location"] = f"/api/trips/{new_trip.trip_id}"

        # Return a JSON response with a success message and the trip ID
        return JSONResponse(content={"message": "Trip created successfully", "trip_id": new_trip.trip_id})

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating trip: {str(e)}")
