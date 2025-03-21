from sqlalchemy import Column, Integer, ForeignKey, Date
from sqlalchemy.orm import relationship

from app.models import Base


class TripDays(Base):
    """
    Model for storing a day in trip information

    trip_day_id: Unique identifier for the trip day
    trip_id: Foreign key to the trip
    day_number: Day number in the trip (Day 1, Day 2 etc.)
    date: Date of the day
    """
    __tablename__ = "trip_days"

    trip_day_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.trip_id"), nullable=False)
    day_number = Column(Integer, nullable=False)  # Day 1, Day 2 etc.
    date = Column(Date)
