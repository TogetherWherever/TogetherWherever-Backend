from sqlalchemy import Column, Integer, ForeignKey, String, Time
from sqlalchemy.orm import relationship

from app.models import Base


class Activities(Base):
    """
    Model for storing activity information in a day

    activity_id: Unique identifier for the activity
    trip_day_id: Foreign key to the trip day
    activity_dest_id: Google Places Destination ID
    activity_dest_name: Name of the destination
    activity_start_time: Start time of the activity
    activity_end_time: End time of the activity
    activity_number: Activity number in the day (Activity 1, Activity 2 etc.)
    """
    __tablename__ = "activities"

    activity_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_day_id = Column(Integer, ForeignKey("trip_days.trip_day_id"), nullable=False)
    activity_dest_id = Column(String, nullable=False)
    activity_dest_name = Column(String)
    activity_start_time = Column(Time)
    activity_end_time = Column(Time)
    activity_number = Column(Integer)  # Activity 1, Activity 2 etc.
