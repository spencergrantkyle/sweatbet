from backend.fastapi.schemas.message import MessageBase, MessageCreate, MessageSchema
from backend.fastapi.schemas.user import (
    UserBase, UserCreate, UserRead,
    StravaTokenBase, StravaTokenCreate, StravaTokenRead,
    StravaAthleteData, StravaTokenResponse, StravaActivity
)
from backend.fastapi.schemas.bet import (
    BetBase, BetCreate, BetUpdate, BetRead, BetSummary,
    BetStatus, ActivityType
)