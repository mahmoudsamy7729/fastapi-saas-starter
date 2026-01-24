from pydantic import BaseModel



class UpdateUserStatusIn(BaseModel):
    is_active: bool

class UpdateUserRoleIn(BaseModel):
    is_admin: bool
