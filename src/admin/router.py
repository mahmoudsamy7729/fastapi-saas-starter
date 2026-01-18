from fastapi import APIRouter
from src.admin import dependencies
from src.auth_bearer import admin_user_dependency



router = APIRouter()



@router.get("/dashboard/stats")
async def get_dashboard_stats():
    pass


@router.get("/users")
async def get_users(user_dependency: dependencies.user_dependency):
    pass


@router.get("/billing/transactions")
async def get_transactions(payment_dependency: dependencies.payment_dependency):
    pass


@router.get("/billing/subscriptions")
async def get_subscriptions(subscription_dependency: dependencies.subscription_dependency):
    pass


