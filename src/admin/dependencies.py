from fastapi import Depends
from typing import Annotated
from src.admin import repository
from src.database import db_dependency
from src.admin.services import UsersService, PaymentsServices, SubscriptionsServices, AnalyticsService



def get_admin_user_dependency(db: db_dependency) -> repository.AdminUserRepository:
    return repository.AdminUserRepository(db)


user_dependency = Annotated[repository.AdminUserRepository, Depends(get_admin_user_dependency)]


def get_users_service(users_repo: user_dependency) -> UsersService:
    return UsersService(users_repo)


UsersServiceDep = Annotated[UsersService,Depends(get_users_service)]


def get_admin_subscription_dependency(db: db_dependency) -> repository.AdminSubscriptionRepository:
    return repository.AdminSubscriptionRepository(db)


subscription_dependency = Annotated[repository.AdminSubscriptionRepository, Depends(get_admin_subscription_dependency)]


def get_subscriptions_service(subscriptions_repo: subscription_dependency) ->SubscriptionsServices:
    return SubscriptionsServices(subscriptions_repo)


SubScriptionsServciceDep = Annotated[SubscriptionsServices, Depends(get_subscriptions_service)]



def get_admin_payment_dependency(db: db_dependency) -> repository.AdminPaymentRepository:
    return repository.AdminPaymentRepository(db)


payment_dependency = Annotated[repository.AdminPaymentRepository, Depends(get_admin_payment_dependency)]


def get_payments_service(payments_repo: payment_dependency) -> PaymentsServices:
    return PaymentsServices(payments_repo)


PaymentsServceDep = Annotated[PaymentsServices,Depends(get_payments_service)]



def get_analytis_service(users_repo: user_dependency,
        subscriptions_repo: subscription_dependency,
        payments_repo: payment_dependency) -> AnalyticsService:
    
    return AnalyticsService(users_repo, subscriptions_repo, payments_repo)


AnalyiticsServiceDep = Annotated[AnalyticsService, Depends(get_analytis_service)]
