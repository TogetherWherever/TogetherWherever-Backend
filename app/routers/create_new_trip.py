from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.trips import Trips
from app.schemas.new_trip import CreateNewTrip

router = APIRouter(prefix="/api/create-new-trip", tags=["create-new-trip"])


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

        return {"message": "Trip created successfully", "trip_id": new_trip.trip_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating trip: {str(e)}")
