from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

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
    dest_lat = Column(Float, nullable=False)
    dest_lon = Column(Float, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration = Column(Integer)  # Number of days
    companion = Column(String)
