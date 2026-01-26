from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.paginate import paginate

from src.admin.models import AdminAuditLog
from src.auth.models import User
from src.billing.models import Subscription, Payment



class AdminUserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def list_users(
        self,
        *,
        is_active: bool | None = None,
        is_verified: bool | None = None,
        is_admin: bool | None = None,
        limit: int = 50,
        offset: int = 0):

        query = select(User).order_by(User.created_at.desc())

        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        if is_verified is not None:
            query = query.where(User.is_verified == is_verified)

        if is_admin is not None:
            query = query.where(User.is_admin == is_admin)
        
        return await paginate(self.db, query, limit=limit, offset=offset)


    async def get_user_by_id(self, user_id: UUID,):
    
        result = await self.db.execute(
            select(User,)
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        subscriptions_count_sq = await self.db.execute(
            select(func.count(Subscription.id)).where(Subscription.user_id == user_id)
        )
        total_subscriptions = subscriptions_count_sq.scalar_one()

        transactions_count_sq = await self.db.execute(
            select(func.count(Payment.id)).where(Payment.user_id == user_id)
        )
        total_transactions = transactions_count_sq.scalar_one()

        return {
            "user": user,
            "subscriptions_count": total_subscriptions,
            "transactions_count": total_transactions,

        }


    async def get_user_subscriptions(self,user_id: UUID,
                    *,
        limit: int = 50,
        offset: int = 0):

        query = select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.started_at.desc())
        

        return await paginate(self.db, query, limit=limit, offset=offset)
    

    async def get_user_transactions(self,user_id: UUID,
                    *,
        limit: int = 50,
        offset: int = 0):
        query = select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc())
        return await paginate(self.db, query, limit=limit, offset=offset)
    

    async def update_user(self, user_id: UUID, **kwargs):
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
            else:
                raise ValueError(f"Invalid field: {key}")
        
        await self.db.commit()
        await self.db.refresh(user)

        return user




class AdminSubscriptionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def list_subscriptions(
        self,
        *,
        limit = 50,
        offset = 0):

        query = select(Subscription).order_by(Subscription.started_at.desc())

        return await paginate(self.db, query, limit=limit, offset=offset)


    async def get_subscription_by_id(self, sub_id: UUID):
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == sub_id).options(selectinload(Subscription.payments)
        ))

        return result.scalar_one_or_none()


class AdminPaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def list_payments(
        self,
        *,
        limit = 50,
        offset = 0):

        query = select(Payment).order_by(Payment.created_at.desc())
        return await paginate(self.db, query, limit=limit, offset=offset)


    async def get_payment_by_id(self, payment_id: UUID):
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id).options(selectinload(Payment.subscription))
        )

        return result.scalar_one_or_none()
    


class AdminAuditLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def list_audit_logs(
        self,
        *,
        admin_id: UUID | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        action: str | None = None,
        limit = 50,
        offset = 0):

        query = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc())

        if admin_id is not None:
            query = query.where(AdminAuditLog.admin_id == admin_id)
        
        if target_type is not None:
            query = query.where(AdminAuditLog.target_type == target_type)
        
        if target_id is not None:
            query = query.where(AdminAuditLog.target_id == target_id)
        
        if action is not None:
            query = query.where(AdminAuditLog.action == action)
        
        return await paginate(self.db, query, limit=limit, offset=offset)
    

    async def log(
        self,
        *,
        admin_id: UUID,
        target_type: str,
        target_id: UUID,
        action: str,
        before: dict | None = None,
        after: dict | None = None,):

        audit_log = AdminAuditLog(
            admin_id=admin_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            before=before,
            after=after,
        )

        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)

        return audit_log
    

    async def get_audit_log_by_id(self, log_id: UUID):
        result = await self.db.execute(
            select(AdminAuditLog).where(AdminAuditLog.id == log_id)
        )

        return result.scalar_one_or_none()
    

