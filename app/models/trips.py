from sqlalchemy import Column, Integer, String, Date, ForeignKey, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Base is used for model class definitions
Base = declarative_base()


class Trips(Base):
    """
    Model for storing trip information

    trip_id: Unique identifier for the trip
    trip_name: Name of the trip
    dest_name: Name of the main destination
    dest_id: Google Places Destination ID
    start_date: Start date of the trip
    end_date: End date of the trip
    duration: Number of days for the trip
    """
    __tablename__ = "trips"

    trip_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    owner = Column(String, ForeignKey("users.username"), nullable=False)
    trip_name = Column(String)
    dest_name = Column(String)
    dest_id = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration = Column(Integer)  # Number of days
    companion = Column(String)

    # Relationship with TripDays
    trip_days = relationship("TripDays", back_populates="trip")


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

    # Relationship with Trips
    trip = relationship("Trips", back_populates="trip_days")

    # Relationship with Activities
    activities = relationship("Activities", back_populates="trip_day")


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

    # Relationship with TripDays
    trip_day = relationship("TripDays", back_populates="activities")
