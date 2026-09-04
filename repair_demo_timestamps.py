"""Populate realistic staggered lifecycle timestamps for existing demo records.
Run manually; normal application startup never fabricates historical events.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

import models
from database import Base, engine, get_db


Base.metadata.create_all(bind=engine)


def ensure_columns():
    from sqlalchemy import inspect, text
    existing = {column["name"] for column in inspect(engine).get_columns("complaints")}
    additions = {
        "acknowledged_at": "DATETIME",
        "in_progress_at": "DATETIME",
        "resolved_at": "DATETIME",
        "updated_at": "DATETIME",
    }
    with engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE complaints ADD COLUMN {name} {sql_type}"))


def main():
    ensure_columns()
    db: Session = next(get_db())
    try:
        complaints = db.query(models.Complaint).order_by(models.Complaint.created_at.asc()).all()
        for index, complaint in enumerate(complaints):
            if not complaint.created_at:
                continue
            base = complaint.created_at
            # Preserve already-recorded real timestamps. Only fill missing demo history.
            if complaint.status in {"Acknowledged", "In Progress", "Resolved"} and complaint.acknowledged_at is None:
                complaint.acknowledged_at = base + timedelta(minutes=7 + index % 5)
            if complaint.status in {"In Progress", "Resolved"} and complaint.in_progress_at is None:
                complaint.in_progress_at = base + timedelta(minutes=22 + index % 9)
            if complaint.status == "Resolved" and complaint.resolved_at is None:
                complaint.resolved_at = base + timedelta(hours=1, minutes=index % 15)
            if complaint.updated_at is None:
                complaint.updated_at = complaint.resolved_at or complaint.in_progress_at or complaint.acknowledged_at or base
        db.commit()
        print(f"Updated {len(complaints)} existing records.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
