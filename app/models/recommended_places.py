from sqlalchemy import Column, Integer, ForeignKey, String

from app.models import Base


class RecommendedPlaces(Base):
    """
    Model for storing recommended places information in a day

    recommended_place_id: Unique identifier for the recommended place
    trip_day_id: Foreign key to the trip day
    dest_id: Google Places Destination ID
    dest_name: Name of the destination
    """
    __tablename__ = "recommended_places"

    recommended_place_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.trip_id"), nullable=False)
    trip_day_id = Column(Integer, ForeignKey("trip_days.trip_day_id"), nullable=False)
    dest_id = Column(String, nullable=False)
    dest_name = Column(String)
