from fastapi import Depends
from typing import Annotated
from src.admin import repository
from src.database import db_dependency



def get_admin_user_dependency(db: db_dependency) -> repository.AdminUserRepository:
    return repository.AdminUserRepository(db)


user_dependency = Annotated[repository.AdminUserRepository, Depends(get_admin_user_dependency)]


def get_admin_subscription_dependency(db: db_dependency) -> repository.AdminSubscriptionRepository:
    return repository.AdminSubscriptionRepository(db)


subscription_dependency = Annotated[repository.AdminSubscriptionRepository, Depends(get_admin_subscription_dependency)]


def get_admin_payment_dependency(db: db_dependency) -> repository.AdminPaymentRepository:
    return repository.AdminPaymentRepository(db)


payment_dependency = Annotated[repository.AdminPaymentRepository, Depends(get_admin_payment_dependency)]
