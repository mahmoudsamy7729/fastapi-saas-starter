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


    async def get_subscriptions(self):
        subscriptions = await self.subscriptions_repo.list_subscriptions()
        return subscriptions['data']
    

class PaymentsServices:
    def __init__(self, payments_repo: AdminPaymentRepository) -> None:
        self.payments_repo = payments_repo


    async def get_payments(self):
        payments = await self.payments_repo.list_payments()
        return payments['data']


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
    

    async def get_user_transactions(self, user_id: UUID):
        transactions = await self.users_repo.get_user_transactions(user_id)
        if not transactions :
            pass
        return transactions
    

    async def get_user_subscriptions(self, user_id: UUID):
        subscriptions = await self.users_repo.get_user_subscriptions(user_id)
        if not subscriptions :
            pass
        return subscriptions
