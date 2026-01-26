from uuid import UUID
from src.admin.repository import (AdminUserRepository, AdminPaymentRepository, 
        AdminSubscriptionRepository, AdminAuditLogRepository)


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
    def __init__(self, users_repo: AdminUserRepository, auditlog_repo: AdminAuditLogRepository) -> None:
        self.users_repo = users_repo
        self.auditlog_repo = auditlog_repo

    
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
    

    async def update_user_status(self, admin_id: UUID, user_id: UUID, is_active: bool):
        user = await self.users_repo.get_user_by_id(user_id)
        if not user:
            pass

        before = {"is_active": user['user'].is_active} #type: ignore
        updated_user = await self.users_repo.update_user(user_id, is_active=is_active)
        after = {"is_active": updated_user.is_active} #type: ignore

        await self.auditlog_repo.log(admin_id=admin_id, target_type="user", target_id=user_id,
            action="user.update_status", before=before, after=after)
        return updated_user
    

    async def update_user_role(self, admin_id: UUID, user_id: UUID, is_admin: bool):
        user = await self.users_repo.get_user_by_id(user_id)
        if not user:
            pass

        before = {"is_admin": user['user'].is_admin} #type: ignore
        updated_user = await self.users_repo.update_user(user_id, is_admin=is_admin)
        after = {"is_admin": updated_user.is_admin} #type: ignore

        await self.auditlog_repo.log(admin_id=admin_id, target_type="user", target_id=user_id, 
                    action="user.update_role", before=before, after=after)
        return updated_user
    

    async def verify_user(self, admin_id: UUID, user_id: UUID):
        user = await self.users_repo.get_user_by_id(user_id)
        if not user:
            pass

        before = {"is_verified": user['user'].is_verified} #type: ignore
        updated_user = await self.users_repo.update_user(user_id, is_verified=True)
        after = {"is_verified": updated_user.is_verified} #type: ignore

        await self.auditlog_repo.log(admin_id=admin_id, target_type="user", target_id=user_id, 
            action="user.verify", before=before, after=after)
        return updated_user
