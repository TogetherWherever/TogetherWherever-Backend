from sqlalchemy import Column, Integer, ForeignKey, String, DateTime

from app.models import Base


class RecentlyView(Base):
    """
    Model for storing recently viewed items by a user

    recent_id: Unique identifier for the recently viewed item
    username: Username of the user who viewed the item
    view_trip_id: ID of the trip that was viewed
    view_date_time: Date and time when the item was viewed
    """
    __tablename__ = "recently_viewed"

    recent_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, ForeignKey("users.username"), nullable=False)
    view_trip_id = Column(Integer, ForeignKey("trips.trip_id"), nullable=False)
    view_date_time = Column(DateTime, nullable=False)
