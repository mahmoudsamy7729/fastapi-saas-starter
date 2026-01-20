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
            "users": users['total'],
            "subscriptions": subscriptions['total'],
            "payments": payments['total']
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

    
    async def get_users(self):
        users = await self.users_repo.list_users()
        return users['data']
    

    async def get_user_by_id(self, user_id : UUID):
        user = await self.users_repo.get_user_by_id(user_id)
        if not user :
            pass
        return user
