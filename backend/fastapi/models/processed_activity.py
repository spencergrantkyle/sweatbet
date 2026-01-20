"""ProcessedActivity model for tracking validated Strava activities."""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from backend.fastapi.dependencies.database import Base


class ProcessedActivity(Base):
    """
    Tracks Strava activities that have already been validated.
    
    This prevents duplicate processing when the scheduler checks for
    new activities, ensuring each activity is only validated once
    against active bets.
    """
    __tablename__ = "processed_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Strava activity identifier - unique to prevent reprocessing
    strava_activity_id = Column(BigInteger, unique=True, index=True, nullable=False)
    
    # User who owns the activity
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Bet that was validated against (if any)
    bet_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("bets.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    # When the activity was processed
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Result of validation: "won", "not_met", "no_active_bets", "error"
    validation_result = Column(String(50), nullable=False)
    
    # Optional details about the validation
    validation_details = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", backref="processed_activities")
    bet = relationship("Bet", backref="processed_activities")

    def __repr__(self):
        return (
            f"<ProcessedActivity(id={self.id}, "
            f"strava_activity_id={self.strava_activity_id}, "
            f"result={self.validation_result})>"
        )

