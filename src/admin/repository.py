from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.paginate import paginate

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


    async def get_user_by_id(self, user_id: UUID):
    
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
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id).limit(limit).offset(offset)
        )

        subscriptions = result.scalars().all()
        return subscriptions
    

    async def get_user_transactions(self,user_id: UUID,
                    *,
        limit: int = 50,
        offset: int = 0):
        result = await self.db.execute(
            select(Payment)
            .where(Payment.user_id == user_id).limit(limit).offset(offset)
        )

        payments = result.scalars().all()
        return payments







class AdminSubscriptionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def list_subscriptions(
        self,
        *,
        limit = 50,
        offset = 0):

        result = await self.db.execute(
            select(Subscription).limit(limit).offset(offset)
        )
        subscriptions = result.scalars().all()
        count_result = await self.db.execute(
            select(func.count()).select_from(Subscription)
        )
        total_subscriptions = count_result.scalar_one()
        return {
            "data": subscriptions,
            "total": total_subscriptions,
            "limit": limit,
            "offset": offset,
        }


    async def get_subscription_by_id(self, sub_id: UUID):
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == sub_id)
        )

        return result.scalar_one_or_none()


class AdminPaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def list_payments(
        self,
        *,
        limit = 50,
        offset = 0):

        result = await self.db.execute(
            select(Payment).limit(limit).offset(offset)
        )

        payments = result.scalars().all()

        count_result = await self.db.execute(
            select(func.count()).select_from(Payment)
        )
        total_payments = count_result.scalar_one()
        return {
            "data": payments,
            "total": total_payments,
            "limit": limit,
            "offset": offset,
        }


    async def get_payment_by_id(self, payment_id: UUID):
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id)
        )

        return result.scalar_one_or_none()