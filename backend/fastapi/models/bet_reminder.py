"""BetReminder model for tracking reminder notifications."""

import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from backend.fastapi.dependencies.database import Base


class BetReminder(Base):
    """
    Tracks when reminder notifications were sent for bets.
    
    This prevents spamming users with too many reminders by
    enforcing a cooldown period between notifications.
    """
    __tablename__ = "bet_reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # One reminder tracker per bet
    bet_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("bets.id", ondelete="CASCADE"), 
        unique=True,
        nullable=False,
        index=True
    )
    
    # When the last reminder was sent (None if never sent)
    last_reminder_sent = Column(DateTime, nullable=True)
    
    # How many reminders have been sent for this bet
    reminder_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    bet = relationship("Bet", backref="reminder_tracking")

    def __repr__(self):
        return (
            f"<BetReminder(id={self.id}, "
            f"bet_id={self.bet_id}, "
            f"reminder_count={self.reminder_count})>"
        )

    @property
    def has_been_reminded(self) -> bool:
        """Check if at least one reminder has been sent."""
        return self.reminder_count > 0

