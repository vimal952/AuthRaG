from datetime import datetime
from database import get_db


async def log_event(
    action: str,
    user_id: str,
    user_email: str,
    role: str,
    **kwargs,
):
    """Central audit logger — call this everywhere an action of interest happens."""
    db = get_db()
    entry = {
        "action": action,
        "user_id": user_id,
        "user_email": user_email,
        "role": role,
        "timestamp": datetime.utcnow(),
        **kwargs,
    }
    await db.audit_logs.insert_one(entry)
