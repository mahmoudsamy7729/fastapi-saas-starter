from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Query
from src.admin import dependencies
from src.auth_bearer import admin_required
from src.admin import schemas
from openai import OpenAI




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
async def get_user_transactions(user_dependency: dependencies.UsersServiceDep, user_id: UUID,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),):
    transactions = await user_dependency.get_user_transactions(user_id, limit=limit, offset=offset)
    return transactions


@router.get("/users/{user_id}/subscriptions")
async def get_user_subscriptions(user_dependency: dependencies.UsersServiceDep, user_id: UUID,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),):
    subscriptions = await user_dependency.get_user_subscriptions(user_id, limit=limit, offset=offset)
    return subscriptions


@router.patch("/users/{user_id}/status")
async def update_user_status(admin: admin_required, user_dependency: dependencies.UsersServiceDep, user_id: UUID,
    data: schemas.UpdateUserStatusIn):
    updated_user = await user_dependency.update_user_status(admin.id, user_id, data.is_active)
    return updated_user


@router.patch("/users/{user_id}/role")
async def update_user_role(admin: admin_required, user_dependency: dependencies.UsersServiceDep, user_id: UUID,
    data: schemas.UpdateUserRoleIn):
    updated_user = await user_dependency.update_user_role(admin.id, user_id, data.is_admin)
    return updated_user


@router.patch("/users/{user_id}/verify")
async def verify_user(admin: admin_required, user_dependency: dependencies.UsersServiceDep, user_id: UUID):
    updated_user = await user_dependency.verify_user(admin.id, user_id)
    return updated_user


@router.get("/billing/transactions")
async def get_transactions(payment_dependency: dependencies.PaymentsServceDep,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),):
    payments = await payment_dependency.get_payments(limit=limit, offset=offset)
    return payments
    

@router.get("/billing/transactions/{payment_id}")
async def get_transaction_by_id(payment_dependency: dependencies.PaymentsServceDep,
    payment_id: UUID):
    payment = await payment_dependency.get_payment_by_id(payment_id)
    return payment


@router.get("/billing/subscriptions")
async def get_subscriptions(subscription_dependency: dependencies.SubScriptionsServciceDep,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),):
    subscriptions = await subscription_dependency.get_subscriptions(limit=limit, offset=offset)
    return subscriptions 


@router.get("/billing/subscriptions/{sub_id}")
async def get_subscription_by_id(subscription_dependency: dependencies.SubScriptionsServciceDep,
    sub_id: UUID):
    subscription = await subscription_dependency.get_subscription_by_id(sub_id)
    return subscription


@router.post("/ai/chat")
async def ai_chat(ai_service: dependencies.AiServiceDep, prompt: str):
    response = await ai_service.call_ai_model(prompt)
    return {"response": response}