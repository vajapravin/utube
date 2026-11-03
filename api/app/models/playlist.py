"""Playlist models."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Playlist(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "playlists"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), default="private", nullable=False)
    system_kind: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        Index(
            "uq_playlists_owner_id_system_kind",
            "owner_id",
            "system_kind",
            unique=True,
            postgresql_where=(system_kind.isnot(None)),
        ),
    )


class PlaylistItem(Base, UUIDMixin):
    __tablename__ = "playlist_items"

    playlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("playlists.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[str] = mapped_column(String(64), default="001000", nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("playlist_id", "video_id", name="uq_playlist_items_playlist_video"),
        Index("ix_playlist_items_position", "playlist_id", "position"),
    )
