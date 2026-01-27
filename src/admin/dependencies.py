from fastapi import Depends
from typing import Annotated
from src.admin import repository
from src.admin.ai_repo import ai_repo
from src.database import db_dependency
from src.admin.services import (UsersService, PaymentsServices,
        SubscriptionsServices, AnalyticsService, AiSerivce)
from src.admin.ai_settings import get_ai_client, ai_model, ai_tools, system


def get_admin_ai_dependency(db: db_dependency) -> ai_repo:
    return ai_repo(db)

ai_dependency = Annotated[ai_repo, Depends(get_admin_ai_dependency)]


def get_ai_service(ai_repo_dep: ai_dependency) -> AiSerivce:
    client = get_ai_client()
    return AiSerivce(ai_repo_dep, client, ai_model, ai_tools, system)

AiServiceDep = Annotated[AiSerivce, Depends(get_ai_service)]

def get_admin_auditlog_dependency(db: db_dependency) -> repository.AdminAuditLogRepository:
    return repository.AdminAuditLogRepository(db)


auditlog_dependency = Annotated[repository.AdminAuditLogRepository, Depends(get_admin_auditlog_dependency)]


def get_admin_auditlog_dependency(db: db_dependency) -> repository.AdminAuditLogRepository:
    return repository.AdminAuditLogRepository(db)


auditlog_dependency = Annotated[repository.AdminAuditLogRepository, Depends(get_admin_auditlog_dependency)]


def get_admin_user_dependency(db: db_dependency) -> repository.AdminUserRepository:
    return repository.AdminUserRepository(db)


user_dependency = Annotated[repository.AdminUserRepository, Depends(get_admin_user_dependency)]


def get_users_service(users_repo: user_dependency, auditlog_repo: auditlog_dependency) -> UsersService:
    return UsersService(users_repo, auditlog_repo)


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