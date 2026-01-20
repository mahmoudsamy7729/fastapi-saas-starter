from fastapi import APIRouter
from src.admin import dependencies
from src.auth_bearer import admin_user_dependency




router = APIRouter()



@router.get("/dashboard/stats")
async def get_dashboard_stats(analytics_depenency: dependencies.AnalyiticsServiceDep):
    stats = await analytics_depenency.get_stats()
    return stats
    


@router.get("/users")
async def get_users(user_dependency: dependencies.UsersServiceDep):
    users = await user_dependency.get_users()
    if users:
        return users
    


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


