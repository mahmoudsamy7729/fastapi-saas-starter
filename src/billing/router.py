from uuid import UUID
from src.rate_limiter import limiter
from fastapi import APIRouter, status, Request, Header
from src.billing import schemas
from src.auth_bearer import  active_user_dep, admin_user_dependency
from src.billing.dependencies import SubscriptionServiceDep, PlanServiceDep, PaymentServiceDep



router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[schemas.PlanOut], status_code=status.HTTP_200_OK)
async def list_plans(PlanService: PlanServiceDep):
    result = await PlanService.retrive_plans()
    return result


@router.post("/plans", response_model=schemas.PlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(admin_user: admin_user_dependency, data: schemas.PlanCreate, PlanService: PlanServiceDep):
    result = await PlanService.create_plan(data)
    if result:
        return result


@router.get("/plans/{plan_id}", response_model=schemas.PlanOut, status_code=status.HTTP_200_OK)
async def get_plan(plan_id: UUID, PlanService: PlanServiceDep):
    plan = await PlanService.get_plan_by_id(plan_id)
    return plan


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(admin_user: admin_user_dependency, plan_id: UUID, PlanService: PlanServiceDep):
    result = await PlanService.soft_delete_plan(plan_id)


@router.patch("/plans/{plan_id}", response_model=schemas.PlanOut, status_code=status.HTTP_200_OK)
async def update_plan(admin_user: admin_user_dependency, plan_id: UUID, data: schemas.PlanUpdate, PlanService: PlanServiceDep):
    return await PlanService.update_plan(plan_id, data)



@router.get("/payments/me", response_model=list[schemas.PaymentResponse], status_code=status.HTTP_200_OK)
async def get_my_payments(user: active_user_dep, PaymentService: PaymentServiceDep):
    payments = await PaymentService.get_my_payments(user)
    return payments


@router.get("/subscriptions/me", response_model=schemas.SubscriptionOut, status_code=status.HTTP_200_OK)
async def get_my_subscription(user: active_user_dep, SubscriptionService: SubscriptionServiceDep):
    subscription = await SubscriptionService.get_user_subscription(user.id)
    return subscription


@router.post("/subscriptions/subscribe", response_model=schemas.CheckoutUrlResponse, status_code=status.HTTP_201_CREATED)
async def subscribe_to_plan(user: active_user_dep, data: schemas.SubscribeRequest,SubscriptionService: SubscriptionServiceDep):
    checkout_url = await SubscriptionService.subscribe_user_to_plan(user, data.plan_code)
    return {"checkout_url":checkout_url}


@router.post("/subscriptions/cancel", response_model=schemas.SubscriptionOut, status_code=status.HTTP_200_OK)
async def cancel_subscription_at_end_of_period(user: active_user_dep, SubscriptionService: SubscriptionServiceDep):
    subscription = await SubscriptionService.cancel_subscription_at_end_of_period(user.id)
    return subscription


@router.post("/subscriptions/upgrade", response_model=schemas.CheckoutUrlResponse, status_code=status.HTTP_200_OK)
async def upgrade_subscription(data: schemas.SubscribeRequest, user: active_user_dep, SubscriptionService: SubscriptionServiceDep):
    sub = await SubscriptionService.upgrade_subscription(user, data.plan_code)
    return sub


@router.post("/stripe/webhook")
@limiter.exempt
async def stripe_webhook(request: Request, SubscriptionService: SubscriptionServiceDep, stripe_signature: str = Header(..., alias="Stripe-Signature")):
    await SubscriptionService.stripe_webhook(request, stripe_signature)
    return True





    
