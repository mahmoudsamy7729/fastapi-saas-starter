from __future__ import annotations

from uuid import uuid4, UUID as PyUUID
from typing import Optional, Any
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    admin_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index= True)
    target_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable= False, index= True)


    action: Mapped[str] = mapped_column(String(50), nullable= False, index= True)

    before: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    after: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                    default=lambda: datetime.now(timezone.utc))
    

Index("ix_admin_audit_target", AdminAuditLog.target_type, AdminAuditLog.target_id)
Index("ix_admin_audit_admin_action", AdminAuditLog.admin_id, AdminAuditLog.action)