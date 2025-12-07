import stripe
from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from src.auth.models import User
from src.auth.repository import UserRepository
from src.billing.models import Plan, Subscription, PaymentProvider, PaymentStatus, SubscriptionStatus
from src.billing.repository import PlanRepository, SubscriptionRepoistory, PaymentRepository
from src.billing.schemas import PlanUpdate
from src.config import settings
from src.logging import get_logger

stripe.api_key = settings.stripe_secret_key
logger = get_logger("billing")


class StripeGateway:
    @staticmethod
    async def save_plan_to_stripe(plan: Plan):
        try:
            if not plan.stripe_product_id:
                logger.info(
                    f"Creating Stripe product for plan_id={plan.id}, name={plan.name}"
                )
                product = await run_in_threadpool(
                    stripe.Product.create,
                    name=plan.name,
                )
                plan.stripe_product_id = product.id
                logger.info(
                    f"Stripe product created for plan_id={plan.id}, stripe_product_id={plan.stripe_product_id}"
                )

            if not plan.stripe_price_id:
                logger.info(
                    f"Creating Stripe price for plan_id={plan.id}, product_id={plan.stripe_product_id}, "
                    f"price_cents={plan.price_cents}, currency={plan.currency}"
                )
                price = await run_in_threadpool(
                    stripe.Price.create,
                    unit_amount=plan.price_cents,   # in cents
                    currency=plan.currency,
                    recurring={"interval": "month"},
                    product=plan.stripe_product_id,
                )
                plan.stripe_price_id = price.id
                logger.info(
                    f"Stripe price created for plan_id={plan.id}, stripe_price_id={plan.stripe_price_id}"
                )

            return plan

        except stripe.StripeError as e:
            logger.error(
                f"Stripe error while saving plan to Stripe plan_id={plan.id}, error={str(e)}"
            )
            return None
        
        except stripe.StripeError as e:
            # handle Stripe errors
            print(f"Stripe error: {e}")
            return None


    @staticmethod
    async def update_plan_in_stripe(plan: Plan, data: PlanUpdate) -> dict:
        update_data = data.model_dump(exclude_unset=True)

        product_update_data = {}
        if "name" in update_data:
            product_update_data["name"] = update_data["name"]

        if product_update_data:
            logger.info(
                f"Updating Stripe product for plan_id={plan.id}, "
                f"stripe_product_id={plan.stripe_product_id}, fields={list(product_update_data.keys())}"
            )
            await run_in_threadpool(
                stripe.Product.update, plan.stripe_product_id, **product_update_data) # type: ignore


         # 2️⃣ If price-related fields changed → create new price
        if any(key in update_data for key in ["price_cents", "billing_period", "currency"]):
            logger.info(
                f"Creating new Stripe price for plan_id={plan.id}, "
                f"stripe_product_id={plan.stripe_product_id}"
            )
            new_price = await run_in_threadpool(
                stripe.Price.create,
                product=plan.stripe_product_id,
                unit_amount=update_data.get("price_cents", plan.price_cents),
                currency=update_data.get("currency", plan.currency),
                recurring={
                    "interval": update_data.get("billing_period", plan.billing_period)
                },
            )
            update_data["stripe_price_id"] = new_price.id
            logger.info(
                f"New Stripe price created for plan_id={plan.id}, stripe_price_id={new_price.id}"
            )

        return update_data

        
    @staticmethod
    async def soft_delete_plan_in_stripe(plan: Plan):
        logger.info(
            f"Soft deleting Stripe product and price for plan_id={plan.id}, "
            f"stripe_product_id={plan.stripe_product_id}, stripe_price_id={plan.stripe_price_id}"
        )
        await run_in_threadpool(stripe.Product.update, plan.stripe_product_id, active=False)  # type: ignore
        await run_in_threadpool(stripe.Price.modify, plan.stripe_price_id, active=False)
        logger.info(
            f"Stripe product and price deactivated for plan_id={plan.id}, "
            f"stripe_product_id={plan.stripe_product_id}, stripe_price_id={plan.stripe_price_id}"
        )


    @staticmethod
    async def ensure_customer(user: User, user_repo: UserRepository) -> User:
        if not user.stripe_customer_id:
            logger.info(
                f"Creating Stripe customer for user_id={str(user.id)}, email={user.email}"
            )
            customer = await run_in_threadpool(stripe.Customer.create,email=user.email,
                metadata={"user_id": str(user.id)})
            user = await user_repo.update(user, stripe_customer_id = customer['id'])
            logger.info(
                f"Stripe customer created for user_id={str(user.id)}, "
                f"email={user.email}, stripe_customer_id={user.stripe_customer_id}"
            )
        else:
            logger.info(
                f"Stripe customer already exists for user_id={str(user.id)}, "
                f"email={user.email}, stripe_customer_id={user.stripe_customer_id}"
            )
        
        return user


    @staticmethod
    async def create_subscription_checkout_session(user: User, plan: Plan,
        user_repo: UserRepository, old_stripe_sub_id: str | None = None ) -> str | None:

        await StripeGateway.ensure_customer(user, user_repo)
        metadata = {
            "plan_id": str(plan.id),
            "plan_code": plan.code,
            "plan_name": plan.name,
            "user_id": str(user.id),
        }
        if old_stripe_sub_id:
            metadata["upgrade_from_subscription_id"] = old_stripe_sub_id
            logger.info(
                f"Creating upgrade checkout session user_id={str(user.id)}, email={user.email}, "
                f"plan_id={plan.id}, old_stripe_sub_id={old_stripe_sub_id}"
            )

        else:
            logger.info(
                f"Creating new subscription checkout session user_id={str(user.id)}, "
                f"email={user.email}, plan_id={plan.id}"
            )


        session = await run_in_threadpool(
            stripe.checkout.Session.create,
            mode="subscription",
            customer=user.stripe_customer_id,        
            line_items=[{
                "price": plan.stripe_price_id,
                "quantity": 1,
            }],
            success_url="https://yourapp.com/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://yourapp.com/cancel",
            client_reference_id=str(user.id),  
            subscription_data={"metadata": metadata},
        )

        logger.info(
            f"Stripe checkout session created user_id={str(user.id)}, email={user.email}, "
            f"plan_id={plan.id}, session_id={session.get('id')}"
        )

        return session.url


    @staticmethod
    async def user_subscribe(session, sub_repo: SubscriptionRepoistory, plan_repo: PlanRepository) -> Subscription:
        user_id = session.get("client_reference_id")
        new_stripe_sub_id = session.get("subscription")
        customer_id = session.get("customer")

        logger.info(
            f"Handling user_subscribe from checkout session user_id={user_id}, "
            f"stripe_subscription_id={new_stripe_sub_id}, stripe_customer_id={customer_id}"
        )

        stripe_subscription = await run_in_threadpool(
            stripe.Subscription.retrieve,
            new_stripe_sub_id,
        )
        sub_metadata = stripe_subscription.get("metadata", {}) or {}
        old_stripe_sub_id = sub_metadata.get("upgrade_from_subscription_id")
        plan_id = sub_metadata.get("plan_id")
        plan = await plan_repo.get_by_id(plan_id) #type: ignore
        if not plan:
            logger.error(
                f"user_subscribe failed: plan not found plan_id={plan_id}, user_id={user_id}"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="error happened")
        if old_stripe_sub_id:
            logger.info(
                f"Handling upgrade: canceling old Stripe subscription old_stripe_sub_id={old_stripe_sub_id}, "
                f"user_id={user_id}"
            )
            await run_in_threadpool(
                stripe.Subscription.delete,
                old_stripe_sub_id,
            )
            await sub_repo.cancel_subscription(
                provider=PaymentProvider.STRIPE,
                provider_subscription_id=old_stripe_sub_id,
                canceled_at=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc),
            )
        sub = await sub_repo.get_by_provider_subscription_id(provider=PaymentProvider.STRIPE,provider_subscription_id=new_stripe_sub_id)
        if not sub:
            sub = await sub_repo.create_subscription(UUID(user_id), UUID(plan_id), PaymentProvider.STRIPE, new_stripe_sub_id, customer_id, SubscriptionStatus.PAST_DUE) 
            logger.info(
                f"Local subscription created from Stripe user_id={user_id}, "
                f"subscription_id={sub.id}, plan_id={plan.id}, provider_subscription_id={new_stripe_sub_id}"
            )
        return sub


    @staticmethod
    async def record_invoice_payment(invoice, subscription: Subscription, payment_repo: PaymentRepository):
        amount_cents = invoice.get("amount_paid")
        currency = (invoice.get("currency") or "usd").upper()
        provider_invoice_id = invoice.get("id")

        logger.info(
            f"Recording invoice payment user_id={str(subscription.user_id)}, "
            f"subscription_id={subscription.id}, provider_invoice_id={provider_invoice_id}, "
            f"amount_cents={amount_cents}, currency={currency}"
        )

        await payment_repo.create_payment(
            user_id=subscription.user_id,
            subscription_id=subscription.id,
            provider=PaymentProvider.STRIPE,
            provider_invoice_id=provider_invoice_id, #type: ignore
            amount_cents=amount_cents, #type: ignore
            currency=currency,
            status=PaymentStatus.SUCCEEDED,
        )


    @staticmethod
    async def cancel_subscription_at_period_end(sub: Subscription) -> tuple[datetime, datetime | None]:
        logger.info(
            f"Requesting Stripe cancel_at_period_end subscription_id={sub.id}, "
            f"provider={sub.provider}, provider_subscription_id={sub.provider_subscription_id}"
        )
        stripe_subscription = None
        if sub.provider == PaymentProvider.STRIPE and sub.provider_subscription_id:
            stripe_subscription = await run_in_threadpool(
                    stripe.Subscription.modify,
                    sub.provider_subscription_id,
                    cancel_at_period_end=True,
                )
        
        now = datetime.now(timezone.utc)
        canceled_at = now
        current_period_end = sub.current_period_end
        
        if stripe_subscription is not None:
            canceled_at_ts = stripe_subscription.get("canceled_at")
            if canceled_at_ts:
                canceled_at = datetime.fromtimestamp(canceled_at_ts, tz=timezone.utc)

            cpe_ts = stripe_subscription.get("current_period_end")
            if cpe_ts:
                current_period_end = datetime.fromtimestamp(cpe_ts, tz=timezone.utc)

        #Current period end stay at the end of the month

        logger.info(
            f"Subscription marked cancel_at_period_end locally subscription_id={sub.id}, "
            f"canceled_at={canceled_at.isoformat()}, current_period_end="
            f"{current_period_end.isoformat() if current_period_end else 'None'}"
        )

        return canceled_at, current_period_end


    @staticmethod
    async def handle_invoice_payment_succeeded(invoice, sub_repo: SubscriptionRepoistory):

        lines = invoice.get("lines", {}).get("data", [])
        if not lines:
            logger.error(
                "handle_invoice_payment_succeeded failed: no lines in invoice "
                f"invoice_id={invoice.get('id')}"
            )
            # For webhooks, don't raise HTTPException → just log and return
            return None
        first_line = lines[0]
        parent = first_line.get("parent", {})
        sub_details = parent.get("subscription_item_details", {}) or {}
        stripe_subscription_id = sub_details.get("subscription")

        if not stripe_subscription_id:
            logger.error(
                "handle_invoice_payment_succeeded failed: no subscription in invoice "
                f"invoice_id={invoice.get('id')}"
            )
            return None
        
        logger.info(
            f"Invoice payment succeeded invoice_id={invoice.get('id')}, "
            f"stripe_subscription_id={stripe_subscription_id}"
        )
        
        stripe_subscription = await run_in_threadpool(
            stripe.Subscription.retrieve,
            stripe_subscription_id,
        )
        subscription_details = stripe_subscription.get("items", {}).get("data", [])
        current_period_start = datetime.fromtimestamp(
             subscription_details[0].get("current_period_start"),
             tz=timezone.utc,
        )    
        current_period_end = datetime.fromtimestamp(
            subscription_details[0].get("current_period_end"),
            tz=timezone.utc,
        )
        sub = await sub_repo.update_subscription_period(
            provider=PaymentProvider.STRIPE,
            provider_subscription_id=stripe_subscription_id,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
        )
        if sub:
            logger.info(
                f"Updated subscription period after invoice success subscription_id={sub.id}, " #type: ignore
                f"user_id={str(sub.user_id)}, current_period_start={current_period_start.isoformat()}, " #type: ignore
                f"current_period_end={current_period_end.isoformat()}"
            )
            return sub
        metadata = stripe_subscription.get("metadata", {}) or {}
        plan_id = metadata.get("plan_id")
        user_id = metadata.get("user_id")
        customer_id = stripe_subscription.get("customer")
        sub = await sub_repo.create_subscription(UUID(user_id), UUID(plan_id), PaymentProvider.STRIPE, stripe_subscription_id, customer_id, SubscriptionStatus.ACTIVE) #type:ignore
        return sub
        

    @staticmethod
    async def handle_invoice_payment_failed(invoice, sub_repo: SubscriptionRepoistory):
        lines = invoice.get("lines", {}).get("data", [])
        if not lines:
            logger.error(
                f"handle_invoice_payment_failed failed: no lines in invoice invoice_id={invoice.get('id')}"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no lines in invoice")
        first_line = lines[0]
        parent = first_line.get("parent", {})
        sub_details = parent.get("subscription_item_details", {}) or {}
        stripe_subscription_id = sub_details.get("subscription")
        logger.warning(
            f"Invoice payment failed invoice_id={invoice.get('id')}, "
            f"stripe_subscription_id={stripe_subscription_id}"
        )
        sub = await sub_repo.update_sub_status(
            provider=PaymentProvider.STRIPE,
            provider_subscription_id=stripe_subscription_id, #type:ignore
            sub_status=SubscriptionStatus.PAST_DUE
        )
        if sub:
            logger.warning(
                f"Subscription marked PAST_DUE subscription_id={sub.id}, "
                f"user_id={str(sub.user_id)}, provider_subscription_id={stripe_subscription_id}"
            )
        else:
            logger.error(
                f"Failed to mark subscription PAST_DUE, local sub not found "
                f"provider_subscription_id={stripe_subscription_id}"
            )
        return sub


    @staticmethod
    async def handle_subscription_deleted(stripe_subscription, sub_repo: SubscriptionRepoistory):
        stripe_subscription_id = stripe_subscription.get("id")
        if not stripe_subscription_id:
            logger.error(
                "handle_subscription_deleted failed: customer.subscription.deleted without id"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="customer.subscription.deleted without id")
        

        logger.info(
            f"Handling subscription deleted from Stripe provider_subscription_id={stripe_subscription_id}"
        )

        canceled_at_ts = stripe_subscription.get("canceled_at")
        if canceled_at_ts:
            canceled_at = datetime.fromtimestamp(canceled_at_ts, tz=timezone.utc)
        else:
            canceled_at = datetime.now(timezone.utc)
        
        current_period_end = datetime.now(timezone.utc)
         #Current period end changes to now so user has no access to the deleted plan

        sub = await sub_repo.cancel_subscription(
            provider=PaymentProvider.STRIPE,
            provider_subscription_id=stripe_subscription_id,
            canceled_at=canceled_at,
            current_period_end=current_period_end,
        )


        if not sub:
            logger.error(
                f"handle_subscription_deleted failed: no local subscription found "
                f"provider_subscription_id={stripe_subscription_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No local subscription found",
            )

        logger.info(
            f"Subscription canceled locally after Stripe deletion subscription_id={sub.id}, "
            f"user_id={str(sub.user_id)}, provider_subscription_id={stripe_subscription_id}"
        )

        return sub
    