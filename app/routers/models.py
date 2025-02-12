from sqlalchemy import Column, Integer, String, Date, ForeignKey, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Base is used for model class definitions
Base = declarative_base()


class Trips(Base):
    __tablename__ = "trips"

    trip_id = Column(Integer, primary_key=True, index=True)
    # user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    trip_name = Column(String)
    dest_name = Column(String)
    dest_id = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration = Column(Integer)  # Number of days

    # Relationship with TripDays
    trip_days = relationship("TripDays", back_populates="trip")


class TripDays(Base):
    __tablename__ = "trip_days"

    trip_day_id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.trip_id"), nullable=False)
    day_number = Column(Integer, nullable=False)  # Day 1, Day 2 etc.
    date = Column(Date)

    # Relationship with Trips
    trip = relationship("Trips", back_populates="trip_days")

    # Relationship with Activities
    activities = relationship("Activities", back_populates="trip_day")


class Activities(Base):
    __tablename__ = "activities"

    activity_id = Column(Integer, primary_key=True, index=True)
    trip_day_id = Column(Integer, ForeignKey("trip_days.trip_day_id"), nullable=False)
    activity_dest_id = Column(String, nullable=False)
    activity_dest_name = Column(String)
    activity_start_time = Column(Time)
    activity_end_time = Column(Time)
    activity_number = Column(Integer)  # Activity 1, Activity 2 etc.

    # Relationship with TripDays
    trip_day = relationship("TripDays", back_populates="activities")
