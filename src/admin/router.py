from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Query
from src.admin import dependencies
from src.auth_bearer import admin_user_dependency




router = APIRouter()



@router.get("/dashboard/stats")
async def get_dashboard_stats(analytics_depenency: dependencies.AnalyiticsServiceDep,):
    stats = await analytics_depenency.get_stats()
    return stats
    


@router.get("/users")
async def get_users(user_dependency: dependencies.UsersServiceDep,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_active: Optional[bool] = Query(None),
    is_verified: Optional[bool] = Query(None),
    is_admin: Optional[bool] = Query(None)):

    users = await user_dependency.get_users(
        limit=limit,
        offset=offset,
        is_active=is_active,
        is_verified=is_verified,
        is_admin=is_admin
    )
    return users
    

@router.get("/users/{user_id}")
async def get_user_details(user_dependency: dependencies.UsersServiceDep, user_id: UUID):
    user = await user_dependency.get_user_by_id(user_id)
    return user


@router.get("/users/{user_id}/transactions")
async def get_user_transactions(user_dependency: dependencies.UsersServiceDep, user_id: UUID):
    transactions = await user_dependency.get_user_transactions(user_id)
    return transactions


@router.get("/users/{user_id}/subscriptions")
async def get_user_subscriptions(user_dependency: dependencies.UsersServiceDep, user_id: UUID):
    subscriptions = await user_dependency.get_user_subscriptions(user_id)
    return subscriptions
    


@router.get("/billing/transactions")
async def get_transactions(payment_dependency: dependencies.PaymentsServceDep):
    payments = await payment_dependency.get_payments()
    if payments:
        return payments
    


@router.get("/billing/subscriptions")
async def get_subscriptions(subscription_dependency: dependencies.SubScriptionsServciceDep):
    subscriptions = await subscription_dependency.get_subscriptions()
    if subscriptions:
        return subscriptions 


