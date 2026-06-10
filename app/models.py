from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def now_hong_kong() -> datetime:
    return datetime.now(ZoneInfo("Asia/Hong_Kong"))


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    problem_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    stdout: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stderr: Mapped[str] = mapped_column(Text, default="", nullable=False)
    execute_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_hong_kong, nullable=False)
