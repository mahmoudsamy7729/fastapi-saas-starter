from typing import Annotated
from fastapi import Depends
from src.auth.repository import UserRepository , LoginCodeRepository
from src.database import db_dependency
from src.auth.emails import Emails
from src.auth.service import UserService
from src.dependencies import token_depedency


#DATABASE DEBENDCIES 
def get_user_repo(db: db_dependency) -> UserRepository:
    return UserRepository(db)

repo_dependency = Annotated[UserRepository, Depends(get_user_repo)]

def get_code_repo(db: db_dependency) -> LoginCodeRepository:
    return LoginCodeRepository(db)

code_dependency = Annotated[LoginCodeRepository, Depends(get_code_repo)]


def get_email_service():
    return Emails()

email_dependency = Annotated[Emails, Depends(get_email_service)]


def get_user_service(user_repo: repo_dependency, 
    login_code_repo: code_dependency, token_repo: token_depedency)-> UserService:
    return UserService(user_repo, token_repo, login_code_repo)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]