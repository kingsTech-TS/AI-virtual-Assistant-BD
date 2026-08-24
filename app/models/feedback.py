from __future__ import annotations

RATING_POSITIVE = "positive"
RATING_NEGATIVE = "negative"
RATINGS = [RATING_POSITIVE, RATING_NEGATIVE]


def new_feedback_doc(
    message_id,
    user_id,
    rating: str,
    comment: str | None = None,
) -> dict:
    from app.utils.helpers import utcnow
    return {
        "message_id": message_id,
        "user_id": user_id,
        "rating": rating,
        "comment": comment,
        "created_at": utcnow(),
    }


def feedback_to_dict(doc) -> dict:
    if not doc:
        return {}
    d = dict(doc)
    d["id"] = str(d["_id"])
    d["_id"] = str(d["_id"])
    d["message_id"] = str(d["message_id"])
    d["user_id"] = str(d["user_id"])
    return d
