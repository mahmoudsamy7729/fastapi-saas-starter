from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


from src.auth.models import User
from src.billing.models import Subscription, Payment



class AdminUserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def list_users(
        self,
        *,
        limit: int = 50,
        offset: int = 0):

        result  = await self.db.execute(
            select(User).limit(limit).offset(offset)
        )
        
        users = result.scalars().all()
        count_result = await self.db.execute(
            select(func.count()).select_from(User)
        )
        total_users = count_result.scalar_one()
        return {
            "data": users,
            "total": total_users,
            "limit": limit,
            "offset": offset,
        }


    async def get_user_by_id(self, user_id: UUID):
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )

        return result.scalar_one_or_none()



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