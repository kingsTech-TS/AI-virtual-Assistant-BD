from enum import Enum
from typing import Dict, List


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_STUDENT = "waiting_for_student"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class PublicationStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


KnowledgeStatus = PublicationStatus
FAQStatus = PublicationStatus


VALID_TICKET_TRANSITIONS: Dict[TicketStatus, List[TicketStatus]] = {
    TicketStatus.OPEN: [
        TicketStatus.IN_PROGRESS,
        TicketStatus.CLOSED,
    ],
    TicketStatus.IN_PROGRESS: [
        TicketStatus.WAITING_FOR_STUDENT,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ],
    TicketStatus.WAITING_FOR_STUDENT: [
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ],
    TicketStatus.RESOLVED: [
        TicketStatus.IN_PROGRESS,
        TicketStatus.CLOSED,
    ],
    TicketStatus.CLOSED: [
        TicketStatus.OPEN,
    ],
}


def is_valid_ticket_transition(from_status: TicketStatus, to_status: TicketStatus) -> bool:
    if from_status == to_status:
        return True
    valid_destinations = VALID_TICKET_TRANSITIONS.get(from_status, [])
    return to_status in valid_destinations
