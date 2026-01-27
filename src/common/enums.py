from enum import Enum
from src.billing.models import PaymentProvider, SubscriptionStatus, PaymentStatus, BillingPeriod
from src.auth.models import Provider as UserProvider

ENUM_CLASSES = [
    SubscriptionStatus,
    PaymentStatus,
    PaymentProvider,
    BillingPeriod,
    UserProvider,
]


# ENUM_COLUMNS = {
#     "subscription_status": SubscriptionStatus,
#     "payment_status": PaymentStatus,
#     "provider": PaymentProvider,
#     "billing_period": BillingPeriod,
# }