"""Audit repository for recording security events."""

import hashlib
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_event(
        self,
        action: str,
        ip_address: str,
        actor_id: Optional[uuid.UUID] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        ip_hash = hashlib.sha256(ip_address.encode("utf-8")).hexdigest()[:16]
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            ip_hash=ip_hash,
            user_agent=user_agent[:500] if user_agent else None,
            meta=meta or {},
        )
        self.db.add(entry)
        await self.db.commit()
        return entry
