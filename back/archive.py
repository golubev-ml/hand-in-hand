"""HIH-1: ленивое архивирование — sold старше недели уходят в archive."""
from datetime import datetime, timedelta

from models import Picture

SOLD_LIFETIME_DAYS = 7


def archive_expired(db) -> int:
    """Переводит просроченные sold в archive. Возвращает число архивированных."""
    cutoff = datetime.now() - timedelta(days=SOLD_LIFETIME_DAYS)
    expired = (
        db.query(Picture)
        .filter(Picture.status == "sold", Picture.sold_at != None, Picture.sold_at < cutoff)  # noqa: E711
        .all()
    )
    for p in expired:
        p.status = "archive"
    if expired:
        db.commit()
    return len(expired)