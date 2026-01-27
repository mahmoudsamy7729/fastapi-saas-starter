import json
from uuid import UUID
from src.admin.utils import json_safe
from src.admin.ai_repo import ai_repo
from src.admin.repository import (AdminUserRepository, AdminPaymentRepository, 
        AdminSubscriptionRepository, AdminAuditLogRepository)







class AnalyticsService:
    def __init__(self,
                users_repo: AdminUserRepository,
                subscriptions_repo: AdminSubscriptionRepository,
                payments_repo: AdminPaymentRepository) -> None:
        self.users_repo = users_repo
        self.subscriptions_repo = subscriptions_repo
        self.payments_repo = payments_repo


    async def get_stats(self):
        users = await self.users_repo.list_users()
        subscriptions = await self.subscriptions_repo.list_subscriptions()
        payments = await self.payments_repo.list_payments()

        return {
            "users": users['total'] if users else 0,
            "subscriptions": subscriptions['total'] if subscriptions else 0,
            "payments": payments['total'] if payments else 0
        }
    
    
class SubscriptionsServices:
    def __init__(self, subscriptions_repo: AdminSubscriptionRepository) -> None:
        self.subscriptions_repo = subscriptions_repo


    async def get_subscriptions(self, limit: int = 50, offset: int = 0):
        subscriptions = await self.subscriptions_repo.list_subscriptions(limit=limit, offset=offset)
        return subscriptions
    

    async def get_subscription_by_id(self, sub_id: UUID):
        subscription = await self.subscriptions_repo.get_subscription_by_id(sub_id)
        return subscription
    

class PaymentsServices:
    def __init__(self, payments_repo: AdminPaymentRepository) -> None:
        self.payments_repo = payments_repo


    async def get_payments(self, limit: int = 50, offset: int = 0):
        payments = await self.payments_repo.list_payments(limit=limit, offset=offset)
        return payments
    

    async def get_payment_by_id(self, payment_id: UUID):
        payment = await self.payments_repo.get_payment_by_id(payment_id)
        return payment


class UsersService:
    def __init__(self, users_repo: AdminUserRepository, auditlog_repo: AdminAuditLogRepository) -> None:
        self.users_repo = users_repo
        self.auditlog_repo = auditlog_repo

    
    async def get_users(self, *,
        limit: int = 50,
        offset: int = 0,
        is_active: bool | None = None,
        is_verified: bool | None = None,
        is_admin: bool | None = None):
        users = await self.users_repo.list_users(
            limit=limit,
            offset=offset,
            is_active=is_active,
            is_verified=is_verified,
            is_admin=is_admin,
        )
        
        return users
    

    async def get_user_by_id(self, user_id : UUID):
        user = await self.users_repo.get_user_by_id(user_id)
        if not user :
            pass
        return user
    

    async def get_user_transactions(self, user_id: UUID,limit: int = 50,
        offset: int = 0):
        transactions = await self.users_repo.get_user_transactions(user_id, limit=limit, offset=offset)
        return transactions
    

    async def get_user_subscriptions(self, user_id: UUID, limit: int = 50,
        offset: int = 0):
        subscriptions = await self.users_repo.get_user_subscriptions(user_id, limit=limit, offset=offset)
        return subscriptions
    

    async def update_user_status(self, admin_id: UUID, user_id: UUID, is_active: bool):
        user = await self.users_repo.get_user_by_id(user_id)
        if not user:
            pass

        before = {"is_active": user['user'].is_active} #type: ignore
        updated_user = await self.users_repo.update_user(user_id, is_active=is_active)
        after = {"is_active": updated_user.is_active} #type: ignore

        await self.auditlog_repo.log(admin_id=admin_id, target_type="user", target_id=user_id,
            action="user.update_status", before=before, after=after)
        return updated_user
    

    async def update_user_role(self, admin_id: UUID, user_id: UUID, is_admin: bool):
        user = await self.users_repo.get_user_by_id(user_id)
        if not user:
            pass

        before = {"is_admin": user['user'].is_admin} #type: ignore
        updated_user = await self.users_repo.update_user(user_id, is_admin=is_admin)
        after = {"is_admin": updated_user.is_admin} #type: ignore

        await self.auditlog_repo.log(admin_id=admin_id, target_type="user", target_id=user_id, 
                    action="user.update_role", before=before, after=after)
        return updated_user
    

    async def verify_user(self, admin_id: UUID, user_id: UUID):
        user = await self.users_repo.get_user_by_id(user_id)
        if not user:
            pass

        before = {"is_verified": user['user'].is_verified} #type: ignore
        updated_user = await self.users_repo.update_user(user_id, is_verified=True)
        after = {"is_verified": updated_user.is_verified} #type: ignore

        await self.auditlog_repo.log(admin_id=admin_id, target_type="user", target_id=user_id, 
            action="user.verify", before=before, after=after)
        return updated_user  


class AiSerivce:
    def __init__(self, ai_repo: ai_repo, client, model: str, tools, system_message: str) -> None:
        self.ai_repo = ai_repo
        self.client = client
        self.model = model
        self.tools = tools
        self.system_message = system_message


    async def get_view_columns(self, view_name: str):
        columns = await self.ai_repo.get_view_columns(view_name)
        return columns
    

    async def execute_ai_sql(self, sql: str, mode: str):
        result = await self.ai_repo.run_ai_sql(sql, mode=mode)
        return result
    

    async def dispatch_tool(self, message):
        responses = []
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments or "{}")
            if name == "get_view_columns":
                view_name = arguments.get("view_name")
                cols = await self.get_view_columns(view_name) #type: ignore
                print(f"Columns for view {view_name}: {cols}")
                responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"columns": cols}, ensure_ascii=False)
                })
            elif name == "execute_sql":
                sql = arguments.get("sql")
                mode = arguments.get("mode", "preview")
                result = await self.execute_ai_sql(sql, mode=mode) #type: ignore
                responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=json_safe, ensure_ascii=False)
                })
            else:
                raise ValueError(f"Unknown tool: {message}")
            
        return responses
    

    async def call_ai_model(self, prompt: str):
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat.completions.create(
            model = self.model,
            messages = messages,
            tools = self.tools
        )
        
        while response.choices[0].finish_reason == "tool_calls":
            print("finish_reason:", response.choices[0].finish_reason)

            assistant_msg = response.choices[0].message

            print("tool_calls:", [tc.function.name for tc in (assistant_msg.tool_calls or [])])

            tool_responses = await self.dispatch_tool(assistant_msg)

            messages.append(assistant_msg)
            messages.extend(tool_responses)

            response = await self.client.chat.completions.create(
                model = self.model,
                messages = messages,
                tools= self.tools,
                tool_choice="auto",
            )

        return response.choices[0].message.content

