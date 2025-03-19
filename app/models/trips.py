from sqlalchemy import Column, Integer, String, Date, ForeignKey
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
    trip_days = relationship("TripDays", back_populates="trips")

    # Relationship with User
    users = relationship("User", back_populates="trips")
