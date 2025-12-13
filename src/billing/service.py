import stripe
from uuid import UUID
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from src.config import settings
from src.billing import schemas
from src.billing.models import PaymentProvider
from src.billing.repository import PlanRepository, SubscriptionRepoistory, PaymentRepository
from src.billing.tasks import (
    send_subscription_email_task,
    send_update_subscription_email_task,
    send_cancel_subscription_email_task,
    send_payment_failed_email_task,
)
from src.billing.utils import serialize_subscription
from src.billing.stripe_gateway import StripeGateway
from src.auth.models import User
from src.auth.repository import UserRepository
from src.logging import get_logger




logger = get_logger("billing")
stripe.api_key = settings.stripe_secret_key


class PlanService:
    @staticmethod
    async def retrive_plans(repo: PlanRepository):
        plans = await repo.list_plans()
        logger.info(f"Retrieved plans count={len(plans)}")
        return plans
    

    @staticmethod
    async def create_plan(data: schemas.PlanCreate, repo: PlanRepository):
        existing_code = await repo.get_by_code(data.code)
        if existing_code :
            logger.warning(f"Attempt to create plan with existing code code={data.code}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Existing Code")
        
        result = await repo.create(data.model_dump())
        logger.info(f"Plan created locally plan_id={result.id}, code={result.code}")
        stripe_plan = await StripeGateway.save_plan_to_stripe(result)
        if stripe_plan:
            updated_plan = await repo.update(result, {
                "stripe_product_id": stripe_plan.stripe_product_id,
                "stripe_price_id": stripe_plan.stripe_price_id
            })
            logger.info(
                f"Plan synced to Stripe plan_id={updated_plan.id}, code={updated_plan.code}, "
                f"stripe_product_id={updated_plan.stripe_product_id}, stripe_price_id={updated_plan.stripe_price_id}"
            )
            return updated_plan
        logger.warning(
            f"Plan created without Stripe sync plan_id={result.id}, code={result.code}"
        )
        return result


    @staticmethod
    async def get_plan_by_id(plan_id: UUID, repo: PlanRepository):
        plan = await repo.get_by_id(plan_id)
        if not plan: 
            logger.warning(f"Plan not found plan_id={plan_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan found for this id")
        return plan
    

    @staticmethod
    async def update_plan(plan_id: UUID, data: schemas.PlanUpdate, repo: PlanRepository):
        plan = await repo.get_by_id(plan_id)
        if not plan: 
            logger.warning(f"Attempt to update non-existing plan plan_id={plan_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan found for this id")
        
        update_data = await StripeGateway.update_plan_in_stripe(plan, data)
        result = await repo.update(plan, update_data)    
        logger.info(f"Plan updated plan_id={result.id}, code={result.code}")
        return result
    

    @staticmethod
    async def soft_delete_plan(plan_id: UUID, repo: PlanRepository):
        plan = await repo.get_by_id(plan_id)
        if not plan: 
            logger.warning(f"Attempt to soft delete non-existing plan plan_id={plan_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan found for this id")
        if not plan.is_active:
            logger.warning(
                f"Attempt to soft delete already inactive plan plan_id={plan.id}, code={plan.code}"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan already deleted.")
       
        await StripeGateway.soft_delete_plan_in_stripe(plan)
        await repo.soft_delete(plan)
        logger.info(
            f"Plan soft deleted plan_id={plan.id}, code={plan.code}, "
            f"stripe_product_id={plan.stripe_product_id}, stripe_price_id={plan.stripe_price_id}"
        )
    


class SubscriptionService:
    @staticmethod
    async def get_user_subscription(user_id: UUID, repo: SubscriptionRepoistory):
        subscription = await repo.get_subscription_with_access(user_id)
        if not subscription:
            logger.warning(f"No active subscription found for user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found for this user.")
        logger.info(
            f"Retrieved active subscription for user_id={user_id}, "
            f"subscription_id={subscription.id}, provider={subscription.provider}"
        )
        return subscription
    

    @staticmethod 
    async def subscribe_user_to_plan(user: User, plan_code: str,
        sub_repo: SubscriptionRepoistory, plan_repo: PlanRepository, user_repo: UserRepository):
        logger.info("Creating subscription", user_id=user.id, plan_code=plan_code)

        logger.info(
            f"Creating subscription user_id={str(user.id)}, email={user.email}, plan_code={plan_code}"
        )
        exisitng_sub = await sub_repo.get_subscription_with_access(user.id)
        if exisitng_sub:
            logger.warning(
                f"Subscription creation rejected: user already has active subscription "
                f"user_id={str(user.id)}, subscription_id={exisitng_sub.id}"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has an active subscription.")
        plan = await plan_repo.get_by_code(plan_code)
        if not plan:
            logger.warning(
                f"Subscription creation failed: plan not found plan_code={plan_code}, user_id={str(user.id)}"
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active plan found for this code.")
        
        checkout_url = await StripeGateway.create_subscription_checkout_session(user, plan, user_repo)
        logger.info(
            f"Stripe checkout session created for subscription user_id={str(user.id)}, "
            f"email={user.email}, plan_code={plan_code}"
        )
        return checkout_url

    
    @staticmethod
    async def cancel_subscription_at_end_of_period(user_id: UUID, sub_repo: SubscriptionRepoistory):
        logger.info(
            f"Cancel subscription at period end requested user_id={str(user_id)}"
        )
        sub = await sub_repo.get_subscription_with_access(user_id)
        if not sub:
            logger.warning(
                f"Cancel subscription failed: no active subscription user_id={str(user_id)}"
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found for this user.")

        if sub.cancel_at_period_end is True: #type: ignore
            logger.warning(
                f"Cancel subscription failed: already set to cancel at period end "
                f"user_id={str(user_id)}, subscription_id={sub.id}"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subscription is already set to cancel at the end of the billing period.")
        
        if sub.provider == PaymentProvider.STRIPE:
            canceled_at, current_period_end = await StripeGateway.cancel_subscription_at_period_end(sub)

        updated_sub = await sub_repo.cancel_subscription(
            provider=sub.provider,
            provider_subscription_id=sub.provider_subscription_id,
            canceled_at=canceled_at,
            current_period_end=current_period_end,
        )
        if updated_sub is None:
            logger.error(
                f"Cancel subscription failed in DB user_id={str(user_id)}, "
                f"provider={sub.provider}, provider_subscription_id={sub.provider_subscription_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found in our database.",
            )
        
        logger.info(
            f"Subscription marked to cancel at period end user_id={str(user_id)}, "
            f"subscription_id={updated_sub.id}, provider={updated_sub.provider}"
        )
        return updated_sub


    @staticmethod
    async def upgrade_subscription(user: User, new_plan_code: str, sub_repo: SubscriptionRepoistory, 
                            plan_repo: PlanRepository, user_repo: UserRepository) :
        
        logger.info(
            f"Upgrade subscription requested user_id={str(user.id)}, "
            f"email={user.email}, new_plan_code={new_plan_code}"
        )

        current_sub = await sub_repo.get_subscription_with_access(user.id)
        if not current_sub:
            logger.warning(
                f"Upgrade subscription failed: no active subscription user_id={str(user.id)}"
            )
            raise HTTPException(status_code=404, detail="No active subscription to upgrade.")
        
        new_plan = await plan_repo.get_by_code(new_plan_code)
        if not new_plan:
            logger.warning(
                f"Upgrade subscription failed: plan not found user_id={str(user.id)}, "
                f"new_plan_code={new_plan_code}"
            )
            raise HTTPException(status_code=404, detail="Plan not found.")
        
        if new_plan.id == current_sub.plan_id:
            logger.warning(
                f"Upgrade subscription rejected: already on this plan user_id={str(user.id)}, "
                f"plan_id={new_plan.id}"
            )
            raise HTTPException(status_code=400, detail="You are already on this plan.")
        
        if current_sub.provider == PaymentProvider.STRIPE:
            checkout_url = await StripeGateway.create_subscription_checkout_session(user, new_plan, user_repo,current_sub.provider_subscription_id)

        logger.info(
            f"Stripe checkout session created for upgrade user_id={str(user.id)}, "
            f"email={user.email}, new_plan_code={new_plan_code}"
        )
        return checkout_url


    @staticmethod
    async def stripe_webhook(request, stripe_signature, sub_repo: SubscriptionRepoistory,
        plan_repo: PlanRepository, payment_repo: PaymentRepository):
        payload = await request.body()
        try:
            event = await run_in_threadpool(
                stripe.Webhook.construct_event,
                payload.decode("utf-8"),
                stripe_signature,
                settings.stripe_webhook_secret
            )
        except Exception as e:
            logger.error(f"Stripe webhook signature verification failed error={str(e)}")
            return {"error": str(e)}
        
        event_type = event["type"]
        data_object = event["data"]["object"]
        logger.info(f"Processing Stripe webhook event_type={event_type}")

        if event_type == "checkout.session.completed":
            session = data_object
            logger.info(
                f"Handling checkout.session.completed for session_id={session.get('id')}"
            )
            sub = await StripeGateway.user_subscribe(session, sub_repo, plan_repo)
            if sub:
                logger.info(
                    f"User subscribed from checkout.session.completed subscription_id={sub.id}, "
                    f"user_id={str(sub.user_id)}, plan_id={str(sub.plan_id)}"
                )
            
        
        if event_type == "invoice.payment_succeeded":
            invoice = data_object
            billing_reason = invoice.get("billing_reason")
            logger.info(
                f"Handling invoice.payment_succeeded invoice_id={invoice.get('id')}, "
                f"billing_reason={billing_reason}"
            )
            sub = await StripeGateway.handle_invoice_payment_succeeded(invoice, sub_repo)
            await StripeGateway.record_invoice_payment(invoice, sub, payment_repo)
            if billing_reason == "subscription_cycle":
                logger.info(
                    f"Sending update subscription email subscription_id={sub.id}, " #type:ignore
                    f"user_id={str(sub.user_id)}" #type:ignore
                )
                send_update_subscription_email_task.delay(serialize_subscription(sub)) #type: ignore
            elif billing_reason == "subscription_create":
                logger.info(
                    f"Sending new subscription email subscription_id={sub.id}, " #type:ignore
                    f"user_id={str(sub.user_id)}" #type:ignore
                )
                send_subscription_email_task.delay(serialize_subscription(sub)) #type: ignore


        if event_type == "customer.subscription.deleted":
            stripe_subscription = data_object
            logger.info(
                f"Handling customer.subscription.deleted stripe_subscription_id={stripe_subscription.get('id')}"
            )
            sub = await StripeGateway.handle_subscription_deleted(stripe_subscription, sub_repo)
            try:
                logger.info(
                    f"Sending cancel subscription email subscription_id={sub.id}, "
                    f"user_id={str(sub.user_id)}"
                )
                send_cancel_subscription_email_task.delay(serialize_subscription(sub))
            except Exception as exc:
                logger.exception(
                    f"Failed to enqueue cancel subscription email subscription_id={sub.id}, "
                    f"user_id={str(sub.user_id)}, error={str(exc)}"
                )
        
        if event_type == "invoice.payment_failed":
            invoice = data_object
            logger.warning(
                f"Handling invoice.payment_failed invoice_id={invoice.get('id')}"
            )
            sub = await StripeGateway.handle_invoice_payment_failed(invoice, sub_repo)
            if sub:
                logger.warning(
                    f"Sending payment failed email subscription_id={sub.id}, "
                    f"user_id={str(sub.user_id)}"
                )
                send_payment_failed_email_task.delay(serialize_subscription(sub))



class PaymentService:
    @staticmethod
    async def get_my_payments(user: User, payment_repo: PaymentRepository):
        payments = await payment_repo.get_my_payments(user.id)
        logger.info(
                f"Retrieved payments for user_id={str(user.id)}, count={len(payments)}"
            )
        return payments