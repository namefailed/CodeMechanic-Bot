from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class BaseEvent:
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BountyFoundEvent(BaseEvent):
    event_type: str = "BOUNTY_FOUND"

@dataclass
class BountyVerifiedEvent(BaseEvent):
    event_type: str = "BOUNTY_VERIFIED"

@dataclass
class PRReadyEvent(BaseEvent):
    event_type: str = "PR_READY"

@dataclass
class PRSubmittedEvent(BaseEvent):
    event_type: str = "PR_SUBMITTED"

@dataclass
class ScamDetectedEvent(BaseEvent):
    event_type: str = "SCAM_DETECTED"

@dataclass
class PRReviewedEvent(BaseEvent):
    event_type: str = "PR_REVIEWED"

@dataclass
class PRRejectedEvent(BaseEvent):
    event_type: str = "PR_REJECTED"

@dataclass
class MaintainerFeedbackEvent(BaseEvent):
    event_type: str = "MAINTAINER_FEEDBACK"
