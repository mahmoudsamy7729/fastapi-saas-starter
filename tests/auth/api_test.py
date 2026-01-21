import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import patch
from httpx import AsyncClient
from fastapi import status
from src.config import settings
from src.hashing import hash_password
from src.jwt import generate_token
from src.auth.models import LoginCode, Provider, User



@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    with patch("src.auth.emails.Emails.send_verification_email") as mock_send_email:
        payload = {
            "email": "sam@example.com",
            "username": "sam",
            "password": "password123"
        }

        response = await client.post("/register", json=payload)
        assert response.status_code == 201
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        assert args[0] == "sam@example.com"
        data = response.json()
        assert data["email"] == payload["email"]
        assert data["username"] == payload["username"]


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient, active_user):
    payload = {
        "email": active_user.email,
        "username": "sam2",
        "password": "password123"
    }

    response = await client.post("/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already exists"


@pytest.mark.asyncio
async def test_register_user_duplicate_username(client: AsyncClient, active_user):
    payload = {
        "email": "sam2@example.com",
        "username": active_user.username,
        "password": "password123"
    }

    response = await client.post("/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already exists"


@pytest.mark.asyncio
async def test_login_user_success(client: AsyncClient, active_user):
    login_payload = {
        "email": active_user.email,
        "password": "123456"
    }

    response = await client.post("/login", json=login_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "refresh_token" in data
    assert "token" in data
    assert data["type"] == "Bearer"
    assert data["user"]["email"] == login_payload["email"]


@pytest.mark.asyncio
async def test_login_user_invalid_email(client: AsyncClient):
    login_payload = {
        "email":"wrongemail@example.com",
        "password": "123456"
    }

    response = await client.post("/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid email or password"
    

@pytest.mark.asyncio
async def test_login_user_invalid_password(client: AsyncClient, active_user):
    login_payload = {
        "email": active_user.email,
        "password": "wrongpassword"
    }

    response = await client.post("/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_user_inactive(client: AsyncClient, disabled_user):
    payload = {
        "email": disabled_user.email,
        "password": "123456"
    }

    response = await client.post("/login", json=payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "User is disabled"


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, active_user):
    login_payload = {
        "email": active_user.email,
        "password": "123456"
    }

    login_response = await client.post("/login", json=login_payload)
    assert login_response.status_code == status.HTTP_200_OK
    refresh_token = login_response.json()["refresh_token"]

    response = await client.post("/refresh-token", params={"token": refresh_token})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "token" in data
    assert data["type"] == "Bearer"

    refresh_response = await client.post("/refresh-token", params={"token": refresh_token})
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token_missing(client: AsyncClient):
    response = await client.post("/refresh-token")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    response = await client.post("/refresh-token", params={"token": "invalidtokenvalue"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid token"


@pytest.mark.asyncio
async def test_change_password_incorrect_old(client: AsyncClient, logged_in_user, auth_headers):
    change_password_payload = {
        "old_password": "wrongoldpassword",
        "new_password": "newpassword123"
    }
    response = await client.post("/change-password", json=change_password_payload, headers=auth_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Old password isn't correct."


@pytest.mark.asyncio
async def test_change_password_success(client: AsyncClient, logged_in_user, auth_headers):
    change_password_payload = {
        "old_password": "123456",
        "new_password": "newpassword123"
    }
    response = await client.post("/change-password", json=change_password_payload, headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Password has been changed successfuly"


@pytest.mark.asyncio
async def test_verify_email_success(client: AsyncClient, unverified_user):
    token, _, _ = generate_token(
        data={"sub": str(unverified_user.id)},
        mins=5,
        secret_key=settings.validation_secret_key,
    )
    response = await client.get("/verify", params={"token": token})
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["message"] == "Email is Verified"


@pytest.mark.asyncio
async def test_verify_email_already_verified(client: AsyncClient, active_user):
    token, _, _ = generate_token(
        data={"sub": str(active_user.id)},
        mins=5,
        secret_key=settings.validation_secret_key,
    )
    response = await client.get("/verify", params={"token": token})
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["message"] == "Email is already Verified"


@pytest.mark.asyncio
async def test_request_verify_email_sends_for_unverified(client: AsyncClient, unverified_user):
    login_payload = {"email": unverified_user.email, "password": "123456"}
    login_response = await client.post("/login", json=login_payload)
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["token"]

    headers = {"Authorization": f"Bearer {token}"}
    with patch("src.auth.emails.Emails.send_verification_email") as mock_send_email:
        response = await client.post("/request/verify", headers=headers)
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["message"] == "New Verification Email has been sent"
        mock_send_email.assert_called_once_with(unverified_user.email, unverified_user.id)


@pytest.mark.asyncio
async def test_request_verify_email_already_verified(client: AsyncClient, logged_in_user, auth_headers):
    with patch("src.auth.emails.Emails.send_verification_email") as mock_send_email:
        response = await client.post("/request/verify", headers=auth_headers)
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["message"] == "Email is already verified"
        mock_send_email.assert_not_called()


@pytest.mark.asyncio
async def test_forget_password_sends_email_when_user_exists(client: AsyncClient, active_user):
    with patch("src.auth.emails.Emails.send_password_reset_email") as mock_send_email:
        response = await client.post("/forget-password", json={"email": active_user.email})
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "password reset link" in response.json()["message"]
        mock_send_email.assert_called_once_with(active_user.email, active_user.id)


@pytest.mark.asyncio
async def test_request_login_code_success(client: AsyncClient, active_user):
    with patch("src.auth.utils.generate_otp_code") as mock_generate, \
        patch("src.auth.emails.Emails.send_login_code") as mock_send_code:
        hashed = await hash_password("123456")
        login_code = LoginCode(
            user_id=active_user.id,
            code_hash=hashed,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        mock_generate.return_value = (login_code, "123456")
        response = await client.post("/request/login-code", json={"email": active_user.email})
        assert response.status_code == status.HTTP_200_OK
        assert "login code" in response.json()["message"]
        mock_send_code.assert_called_once_with(active_user.email, "123456")


@pytest.mark.asyncio
async def test_login_with_code_success(client: AsyncClient, active_user):
    with patch("src.auth.utils.generate_otp_code") as mock_generate, \
        patch("src.auth.emails.Emails.send_login_code"):
        hashed = await hash_password("123456")
        login_code = LoginCode(
            user_id=active_user.id,
            code_hash=hashed,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        mock_generate.return_value = (login_code, "123456")
        await client.post("/request/login-code", json={"email": active_user.email})

    response = await client.post("/login/code", json={"email": active_user.email, "code": "123456"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user"]["email"] == active_user.email
    assert data["type"] == "Bearer"


@pytest.mark.asyncio
async def test_google_login_redirect(client: AsyncClient):
    with patch("src.auth.router.utils.get_google_login_url") as mock_url:
        mock_url.return_value = ("https://accounts.google.com/o/oauth2/auth", "state123")
        response = await client.get("/google/login", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert response.headers["location"] == "https://accounts.google.com/o/oauth2/auth"


@pytest.mark.asyncio
async def test_google_callback_success(client: AsyncClient):
    fake_user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        provider=Provider.GOOGLE,
    )
    with patch("src.auth.service.UserService.login_with_google") as mock_login:
        mock_login.return_value = ("access", fake_user, "refresh")
        response = await client.get("/auth/social/callback/google")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["token"] == "access"
        assert data["refresh_token"] == "refresh"


@pytest.mark.asyncio
async def test_github_login_redirect(client: AsyncClient):
    with patch("src.auth.router.utils.get_github_login_url") as mock_url:
        mock_url.return_value = ("https://github.com/login/oauth/authorize", "state123")
        response = await client.get("/github/login", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert response.headers["location"] == "https://github.com/login/oauth/authorize"


@pytest.mark.asyncio
async def test_github_callback_success(client: AsyncClient):
    fake_user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        provider=Provider.GITHUB,
    )
    with patch("src.auth.service.UserService.login_with_github") as mock_login:
        mock_login.return_value = ("access", fake_user, "refresh")
        response = await client.get("/auth/social/callback/github")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["token"] == "access"
        assert data["refresh_token"] == "refresh"
