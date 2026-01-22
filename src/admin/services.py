from uuid import UUID
from src.admin.repository import AdminUserRepository, AdminPaymentRepository, AdminSubscriptionRepository


class AnalyticsService:
    def __init__(self,
                users_repo: AdminUserRepository,
                subscriptions_repo: AdminSubscriptionRepository,
                payments_repo: AdminPaymentRepository) -> None:
        self.users_repo = users_repo
        self.subscriptions_repo = subscriptions_repo
        self.payments_repo = payments_repo


    async def get_stats(self):
        users = await self.users_repo.list_users()
        subscriptions = await self.subscriptions_repo.list_subscriptions()
        payments = await self.payments_repo.list_payments()

        return {
            "users": users['total'] if users else 0,
            "subscriptions": subscriptions['total'] if subscriptions else 0,
            "payments": payments['total'] if payments else 0
        }
    
    
class SubscriptionsServices:
    def __init__(self, subscriptions_repo: AdminSubscriptionRepository) -> None:
        self.subscriptions_repo = subscriptions_repo


    async def get_subscriptions(self, limit: int = 50, offset: int = 0):
        subscriptions = await self.subscriptions_repo.list_subscriptions(limit=limit, offset=offset)
        return subscriptions
    

    async def get_subscription_by_id(self, sub_id: UUID):
        subscription = await self.subscriptions_repo.get_subscription_by_id(sub_id)
        return subscription
    

class PaymentsServices:
    def __init__(self, payments_repo: AdminPaymentRepository) -> None:
        self.payments_repo = payments_repo


    async def get_payments(self, limit: int = 50, offset: int = 0):
        payments = await self.payments_repo.list_payments(limit=limit, offset=offset)
        return payments
    

    async def get_payment_by_id(self, payment_id: UUID):
        payment = await self.payments_repo.get_payment_by_id(payment_id)
        return payment


class UsersService:
    def __init__(self, users_repo: AdminUserRepository) -> None:
        self.users_repo = users_repo

    
    async def get_users(self, *,
        limit: int = 50,
        offset: int = 0,
        is_active: bool | None = None,
        is_verified: bool | None = None,
        is_admin: bool | None = None):
        users = await self.users_repo.list_users(
            limit=limit,
            offset=offset,
            is_active=is_active,
            is_verified=is_verified,
            is_admin=is_admin,
        )
        
        return users
    

    async def get_user_by_id(self, user_id : UUID):
        user = await self.users_repo.get_user_by_id(user_id)
        if not user :
            pass
        return user
    

    async def get_user_transactions(self, user_id: UUID,limit: int = 50,
        offset: int = 0):
        transactions = await self.users_repo.get_user_transactions(user_id, limit=limit, offset=offset)
        return transactions
    

    async def get_user_subscriptions(self, user_id: UUID, limit: int = 50,
        offset: int = 0):
        subscriptions = await self.users_repo.get_user_subscriptions(user_id, limit=limit, offset=offset)
        return subscriptions
