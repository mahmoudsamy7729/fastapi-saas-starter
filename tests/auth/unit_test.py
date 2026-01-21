import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone, UTC
from fastapi import HTTPException
from starlette.requests import Request as StarletteRequest
from starlette.datastructures import QueryParams
from unittest.mock import AsyncMock, patch
from src.hashing import verify_password, hash_password
from src.jwt import generate_token, verify_token
from src.auth.service import UserService
from src.auth.models import User, Provider, LoginCode
from src.auth.schemas import UserCreateRequest, UserLoginRequest, NewPasswordRequest, ChangePasswordRequest, ForgetPasswordRequest, LoginCodeRequest, LoginWithCodeRequest


@pytest.mark.asyncio
async def test_hash_and_verify_password():
    passowrd = "securepassword123"
    hashed = await hash_password(passowrd)
    assert await verify_password(passowrd, hashed) is True
    assert await verify_password("wrongpassword", hashed) is False


@pytest.mark.asyncio
async def test_generate_and_verify_token_success():
    data = {"sub": "user123"}
    token, _, _ = generate_token(data=data, mins=1, secret_key="secret_key")
    payload = verify_token(token=token, secret_key="secret_key")
    assert payload["sub"] == "user123"


@pytest.mark.asyncio
async def test_verify_token_invalid_signature():
    data = {"sub": "user123"}
    token, _, _ = generate_token(data=data, mins=1, secret_key="secret_key")
    with pytest.raises(HTTPException):
        verify_token(token=token, secret_key="wrong_secret_key")


@pytest.mark.asyncio
async def test_verify_token_missing_sub():
    data = {"name": "user123"}
    token, _, _ = generate_token(data=data, mins=1, secret_key="secret_key")
    with pytest.raises(HTTPException):
        verify_token(token=token, secret_key="secret_key")


@pytest.mark.asyncio
async def test_verify_token_invalid():
    invalid_token = "this.is.an.invalid.token"
    with pytest.raises(HTTPException):
        verify_token(token=invalid_token, secret_key="secret_key")

    
@pytest.mark.asyncio
async def test_verify_token_expired():
    data = {"sub": "user123"}
    token, _, _ = generate_token(data=data, mins=-1, secret_key="secret_key")
    with pytest.raises(HTTPException):  
        verify_token(token=token, secret_key="secret_key")


@pytest.mark.asyncio
async def test_user_registration():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None
    user_repo.get_by_username.return_value = None

    mock_user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        password="hashed",
        provider=Provider.LOCAL
    )

    user_repo.create.return_value = mock_user
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    with patch("src.auth.service.hash_password", new=AsyncMock(return_value="hashed")):
        user_data = UserCreateRequest(
            email="sam@example.com",
            username="sam",
            password="123456"
        )

        result = await service.register_user(user_data)
        assert result.email == "sam@example.com"
        user_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_register_existing_email():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = User()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    user_data = UserCreateRequest(
        email="sam@example.com",
        username="sam",
        password="123456"
    )

    with pytest.raises(HTTPException) as exc:
        await service.register_user(user_data)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_user_register_existing_username():
    user_repo = AsyncMock()
    user_repo.get_by_username.return_value = User()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    user_data = UserCreateRequest(
        email="sam@example.com",
        username="sam",
        password="123456"
    )

    with pytest.raises(HTTPException) as exc:
        await service.register_user(user_data)

    assert exc.value.status_code == 400
    

@pytest.mark.asyncio
async def test_login_user_success():
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        password="hashed",
        is_active=True,
    )

    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = user
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    with patch("src.auth.service.verify_password", new_callable=AsyncMock) as mock_verify, \
            patch("src.auth.service.generate_token") as mock_generate, \
            patch("src.auth.service.store_refresh_token_in_db", new_callable=AsyncMock) as mock_store:
        
        mock_verify.return_value = True
        mock_generate.side_effect = [
            ("access", "jti_access", 123456),
            ("refresh", "jti_refresh", 123999),
        ]
        mock_store.return_value = None

        user_data = UserLoginRequest(email="sam@example.com", password="123456")
        access, user_out, refresh = await service.login_user(user_data)

        assert access == "access"
        assert refresh == "refresh"
        assert user_out.email == "sam@example.com"


@pytest.mark.asyncio
async def test_login_user_invalid_password():
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        password="hashed",
        is_active=True,
    )

    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = user
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)
    with patch("src.auth.service.verify_password", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = False

        user_data = UserLoginRequest(email="sam@example.com", password="123456")

        with pytest.raises(HTTPException) as exc:
            await service.login_user(user_data)


@pytest.mark.asyncio
async def test_login_user_invalid_email():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    user_data = UserLoginRequest(email="sam@example.com", password="123456")

    with pytest.raises(HTTPException) as exc:
        await service.login_user(user_data)


@pytest.mark.asyncio
async def test_login_user_inactive():
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        password="hashed",
        is_active=False,
    )

    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = user
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    with patch("src.auth.service.verify_password", new_callable=AsyncMock) as mock_verify:
           
        mock_verify.return_value = True

        user_data = UserLoginRequest(email="sam@example.com", password="123456")
        with pytest.raises(HTTPException) as exc:
            await service.login_user(user_data)


@pytest.mark.asyncio
async def test_refresh_token_success():
    refresh_token = "valid_refresh_token"
    token_repo = AsyncMock()
    old_token = AsyncMock()
    token_repo.get_by_jti.return_value = old_token
    user_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    payload = {
        "sub": "12345678-1234-5678-1234-567812345678",
        "email": "test@example.com",
        "jti": "jti123",
        "iat": 1620000000,
        "exp": 1620003600
    }

    with patch("src.auth.service.verify_token", return_value=payload), \
         patch("src.auth.service.validate_refresh_token", return_value=None), \
         patch("src.auth.service.generate_token", side_effect=[("access_token", None, None), ("refresh_token", "jti123", 999999)]), \
         patch("src.auth.service.hash_password", new_callable=AsyncMock, return_value="hashed_refresh"), \
         patch("src.auth.service.revoke_refresh_token", new_callable=AsyncMock, return_value=None):
        
        access, refresh = await service.refresh_token(refresh_token)

        assert access == "access_token"
        assert refresh == "refresh_token"
        token_repo.get_by_jti.assert_awaited_once_with("jti123")


@pytest.mark.asyncio 
async def test_refresh_token_no_jti():
    refresh_token = "invalid_refresh_token"
    payload = {
        "sub": "12345678-1234-5678-1234-567812345678",
        "email": "test@example.com",
        "iat": 1620000000,
        "exp": 1620003600
    }

    with patch("src.auth.service.verify_token", return_value=payload):
        user_repo = AsyncMock()
        token_repo = AsyncMock()
        login_code_repo = AsyncMock()
        service = UserService(user_repo, token_repo, login_code_repo)
        with pytest.raises(HTTPException) as exc:
            await service.refresh_token(refresh_token)


@pytest.mark.asyncio
async def test_refresh_token_not_found():
    refresh_token = "valid_refresh_token"
    token_repo = AsyncMock()
    token_repo.get_by_jti.return_value = None
    user_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    payload = {
        "sub": "12345678-1234-5678-1234-567812345678",
        "email": "test@example.com",
        "jti": "jti123",
        "iat": 1620000000,
        "exp": 1620003600
    }

    with patch("src.auth.service.verify_token", return_value=payload), \
         patch("src.auth.service.validate_refresh_token", side_effect=HTTPException(status_code=401)):
        
        with pytest.raises(HTTPException) as exc:
            await service.refresh_token(refresh_token)


@pytest.mark.asyncio
async def test_refresh_token_revoked():
    refresh_token = "valid_refresh_token"
    token_repo = AsyncMock()
    old_token = AsyncMock()
    old_token.revoked = True
    token_repo.get_by_jti.return_value = old_token
    user_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    payload = {
        "sub": "12345678-1234-5678-1234-567812345678",
        "email": "test@example.com",
        "jti": "jti123",
        "iat": 1620000000,
        "exp": 1620003600
    }

    with patch("src.auth.service.verify_token", return_value=payload), \
         patch("src.auth.service.validate_refresh_token", side_effect=HTTPException(status_code=401)):
        
        with pytest.raises(HTTPException) as exc:
            await service.refresh_token(refresh_token)


@pytest.mark.asyncio
async def test_refresh_token_missing_value():
    user_repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    with pytest.raises(HTTPException) as exc:
        await service.refresh_token("")


@pytest.mark.asyncio
async def test_refresh_token_invalid_token():
    refresh_token = "invalid_refresh_token"
    user_repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    with patch("src.auth.service.verify_token", side_effect=HTTPException(status_code=401)):
        with pytest.raises(HTTPException) as exc:
            await service.refresh_token(refresh_token)


@pytest.mark.asyncio
async def test_validate_user():
    user_repo = AsyncMock()
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        password="hashed",
        is_active=True,
        is_verified=False
    )
    token = "valid_token"
    user_repo.get_by_id.return_value = user
    user_repo.update = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    payload = {"sub": str(user.id)}

    with patch("src.auth.service.verify_token", return_value=payload):
        result = await service.validate_user(token)
        assert result is True
        user_repo.update.assert_awaited_once_with(user)
        assert user.is_verified is True


@pytest.mark.asyncio
async def test_validate_user_invalid_token():
    user_repo = AsyncMock()
    token = "invalid_token"
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        password="hashed",
        is_active=True,
        is_verified=True
    )

    user_repo.get_by_id.return_value = user
    user_repo.update = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    payload = {"sub": str(user.id)}

    with patch("src.auth.service.verify_token", return_value=payload):
        result = await service.validate_user(token)
        assert result is False
        user_repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_user_user_not_found():
    user_repo = AsyncMock()
    token = "valid_token"
    user_repo.get_by_id.return_value = None
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)
    payload = {"sub": str(uuid4())}
    with patch("src.auth.service.verify_token", return_value=payload):
        
        with pytest.raises(HTTPException) as exc:
            await service.validate_user(token)


@pytest.mark.asyncio
async def test_forget_password_user_found():
    user_repo = AsyncMock()
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        is_active=True,
        is_verified=True
    )
    user_repo.get_by_email.return_value = user
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    data = ForgetPasswordRequest(email="sam@example.com")
    result = await service.forget_password(data)
    assert result == user


@pytest.mark.asyncio
async def test_forget_password_user_missing():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    data = ForgetPasswordRequest(email="missing@example.com")
    result = await service.forget_password(data)
    assert result is None


@pytest.mark.asyncio
async def test_new_password():
    user_repo = AsyncMock()
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        password="hashed",
        is_active=True,
        is_verified=True
    ) 
    user_repo.get_by_id.return_value = user
    user_repo.update = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)
    token = "valid_token"
    new_password = "new_secure_password"

    with patch("src.auth.service.verify_token", return_value={"sub": str(user.id)}), \
         patch("src.auth.service.hash_password", new=AsyncMock(return_value="new_hashed_password")):
        
        data = NewPasswordRequest(password=new_password, token = token)
        result = await service.new_password(data)
        assert result is True
        assert user.password == "new_hashed_password"
        user_repo.update.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_new_password_user_not_found():
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = None
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)
    token = "valid_token"
    new_password = "new_secure_password"

    with patch("src.auth.service.verify_token", return_value={"sub": str(uuid4())}), \
         patch("src.auth.service.hash_password", new=AsyncMock(return_value="new_hashed_password")):
        
        data = NewPasswordRequest(password=new_password, token = token)
        with pytest.raises(HTTPException) as exc:
            await service.new_password(data)  


@pytest.mark.asyncio
async def test_change_password():
    user_repo = AsyncMock()
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        password="hashed",
        is_active=True,
        is_verified=True
    ) 
    user_repo.update = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)

    with patch("src.auth.service.verify_password", new_callable=AsyncMock) as mock_verify, \
        patch("src.auth.service.hash_password", new_callable=AsyncMock) as mock_hash:
        data = ChangePasswordRequest(new_password="new_hashed_password", old_password="hashed")
        mock_verify.return_value = True
        mock_hash.return_value = "new_hashed_password"
        result = await service.change_password(data, user)
        assert result is True
        assert user.password == "new_hashed_password"
        user_repo.update.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_change_password_invalid_old_password():
    user_repo = AsyncMock()
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        password="hashed",
        is_active=True,
        is_verified=True
    ) 

    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)
    with patch("src.auth.service.verify_password", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = False 
        data = ChangePasswordRequest(new_password="new_hashed_password", old_password="wrong_old_password")
        with pytest.raises(HTTPException) as exc:
            await service.change_password(data, user)


@pytest.mark.asyncio
async def test_deactivate_user_success():
    user_repo = AsyncMock()
    user_repo.update = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(user_repo, token_repo, login_code_repo)
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        is_active=True,
        is_verified=True
    )

    result = await service.deactivate_user(user)
    assert result is True
    assert user.is_active is False
    user_repo.update.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_request_login_code():
    user_repo = AsyncMock()
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        is_active=True,
        is_verified=True
    ) 
    user_repo.get_by_email.return_value = user
    code_repo = AsyncMock()
    token_repo = AsyncMock()
    service = UserService(user_repo, token_repo, code_repo)
    otp_code_obj = "login_code_obj"
    code_value = "123456"

    request_data = LoginCodeRequest(email="sam@example.com")

    with patch("src.auth.service.utils.generate_otp_code", return_value=(otp_code_obj, code_value)):
        returned_user, returned_code = await service.login_code(request_data)
    
        assert returned_user == user
        assert returned_code == code_value
        user_repo.get_by_email.assert_awaited_once_with("sam@example.com")
        code_repo.delete.assert_awaited_once_with(user.id)
        code_repo.create.assert_awaited_once_with(otp_code_obj)


@pytest.mark.asyncio
async def test_request_login_code_user_not_found():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None
    code_repo = AsyncMock()
    token_repo = AsyncMock()
    service = UserService(user_repo, token_repo, code_repo)

    request_data = LoginCodeRequest(email="sam@example.com")
    with pytest.raises(HTTPException) as exc:
        await service.login_code(request_data)


@pytest.mark.asyncio
async def test_login_with_code_success():
    user_repo = AsyncMock()
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        is_active=True,
        is_verified=True
    )

    user_repo.get_by_email.return_value = user
    code_repo = AsyncMock()
    token_repo = AsyncMock()
    service = UserService(user_repo, token_repo, code_repo)
    code = LoginCode(
        user_id = user.id,
        code_hash = "hashed_code",
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    code_repo.get_latest_for_user.return_value = code

    with patch("src.auth.service.verify_password", new_callable=AsyncMock) as mock_verify, \
        patch("src.auth.service.generate_token") as mock_generate, \
        patch("src.auth.service.store_refresh_token_in_db", new_callable=AsyncMock) as mock_store:

        data = LoginWithCodeRequest(email="sam@example.com", code="123456")
        mock_generate.side_effect = [("access", "jti123", 123456), ("refresh", "jti999", 999999)]
        mock_store.return_value = None
        mock_verify.return_value = True
        access_token, user, refresh_token = await service.login_with_code(data)
        assert access_token == "access"
        assert refresh_token == "refresh"
        assert user.email == "sam@example.com"
        code_repo.delete.assert_awaited_once_with(user.id)
        

@pytest.mark.asyncio
async def test_login_with_code_expired_code():
    user_repo = AsyncMock()
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        is_active=True,
        is_verified=True
    )

    user_repo.get_by_email.return_value = user
    code_repo = AsyncMock()
    token_repo = AsyncMock()
    service = UserService(user_repo, token_repo, code_repo)
    code = LoginCode(
        user_id = user.id,
        code_hash = "hashed_code",
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=-5)
    )
    code_repo.get_latest_for_user.return_value = code

    data = LoginWithCodeRequest(email="sam@example.com", code="123456")

    with pytest.raises(HTTPException) as exc:
        await service.login_with_code(data)


@pytest.mark.asyncio
async def test_login_with_no_code_found():
    user_repo = AsyncMock()
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        is_active=True,
        is_verified=True
    )

    user_repo.get_by_email.return_value = user
    code_repo = AsyncMock()
    token_repo = AsyncMock()
    service = UserService(user_repo, token_repo, code_repo)
    code_repo.get_latest_for_user.return_value = None

    data = LoginWithCodeRequest(email="sam@example.com", code="123456")

    with pytest.raises(HTTPException) as exc:
        await service.login_with_code(data)

@pytest.mark.asyncio
async def test_login_with_code_invalid_code():
    user_repo = AsyncMock()
    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        is_active=True,
        is_verified=True
    )

    user_repo.get_by_email.return_value = user
    code_repo = AsyncMock()
    token_repo = AsyncMock()
    service = UserService(user_repo, token_repo, code_repo)
    code = LoginCode(
        user_id = user.id,
        code_hash = "hashed_code",
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    code_repo.get_latest_for_user.return_value = code

    data = LoginWithCodeRequest(email="sam@example.com", code="123456")
    with patch("src.auth.service.verify_password", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = False

        with pytest.raises(HTTPException) as exc:
            await service.login_with_code(data)


@pytest.mark.asyncio
async def test_login_with_google_success():
    scope = {
        "type": "http",
        "query_string": b"code=valid_code&state=123",
        "headers": []
    }
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"code": "valid_code", "state": "123"})
    request._cookies = {"oauth_state_google": "123"}


    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    # User doesn't exist -> will be created
    repo.get_by_email.return_value = None

    created_user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        provider=Provider.GOOGLE,
        is_verified=True
    )

    repo.create.return_value = created_user

    # -----------------------------
    # 3) Patching external functions
    # -----------------------------
    with patch("src.auth.utils.google_tokens", return_value="google_token"), \
         patch("src.auth.utils.get_user_info", return_value=("sam@example.com", "sam")), \
         patch("src.auth.service.generate_token", side_effect=[
        ("access123", "jti_access", 111),
        ("refresh123", "jti_refresh", 222),
]), \
         patch("src.auth.service.store_refresh_token_in_db", new_callable=AsyncMock, return_value=None):
        
        access, user, refresh = await service.login_with_google(request)

        assert access == "access123"
        assert refresh == "refresh123"     # because mocked generate_token returns same tuple
        assert user.email == "sam@example.com"
        assert user.username == "sam"

        repo.get_by_email.assert_awaited_once_with("sam@example.com")
        repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_with_google_missing_params():
    scope = {"type": "http", "query_string": b"", "headers": []}
    request = StarletteRequest(scope)
    request._query_params = QueryParams({})
    request._cookies = {"oauth_state_google": "123"}

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    with pytest.raises(HTTPException) as exc:
        await service.login_with_google(request)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid OAuth callback"


@pytest.mark.asyncio
async def test_login_with_google_missing_cookie_state():
    scope = {
        "type": "http",
        "query_string": b"code=valid&state=xyz",
        "headers": []
    }
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"code": "valid", "state": "xyz"})
    request._cookies = {}  # cookie missing

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    with pytest.raises(HTTPException) as exc:
        await service.login_with_google(request)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid OAuth callback"


@pytest.mark.asyncio
async def test_login_with_google_state_mismatch():
    scope = {
        "type": "http",
        "query_string": b"code=valid&state=abc",
        "headers": []
    }
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"code": "valid", "state": "abc"})
    request._cookies = {"oauth_state_google": "XYZ"}  # mismatch

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    with pytest.raises(HTTPException) as exc:
        await service.login_with_google(request)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid OAuth state"


@pytest.mark.asyncio
async def test_login_with_google_google_tokens_error():
    scope = {
        "type": "http",
        "query_string": b"code=valid_code&state=123",
        "headers": []
    }
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"code": "valid_code", "state": "123"})
    request._cookies = {"oauth_state_google": "123"}

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    with patch("src.auth.utils.google_tokens", side_effect=Exception("Google failure")):
        with pytest.raises(Exception) as exc:
            await service.login_with_google(request)

        assert str(exc.value) == "Google failure"


@pytest.mark.asyncio
async def test_login_with_google_user_exists():
    scope = {
        "type": "http",
        "query_string": b"code=valid&state=123",
        "headers": []
    }
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"code": "valid", "state": "123"})
    request._cookies = {"oauth_state_google": "123"}

    user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        provider=Provider.GOOGLE,
        is_verified=True
    )

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    repo.get_by_email.return_value = user  # user already exists

    with patch("src.auth.utils.google_tokens", return_value="google_token"), \
         patch("src.auth.utils.get_user_info", return_value=("sam@example.com", "sam")), \
         patch("src.auth.service.generate_token", side_effect=[
             ("accessXYZ", "j1", 111),
             ("refreshXYZ", "j2", 222)
         ]), \
         patch("src.auth.service.store_refresh_token_in_db", new_callable=AsyncMock, return_value=None):

        access, out_user, refresh = await service.login_with_google(request)

        assert access == "accessXYZ"
        assert refresh == "refreshXYZ"
        assert out_user.email == user.email

        repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_login_with_github_success():
    scope = {
        "type": "http",
        "query_string": b"code=valid_code&state=abc",
        "headers": []
    }
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"code": "valid_code", "state": "abc"})
    request._cookies = {"oauth_state_github": "abc"}

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    repo.get_by_email.return_value = None  # user does not exist

    created_user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        provider=Provider.GITHUB,
        is_verified=True
    )
    repo.create.return_value = created_user

    with patch("src.auth.utils.github_tokens", return_value="github_token"), \
         patch("src.auth.utils.get_github_user_info", return_value=("sam@example.com", "sam")), \
         patch("src.auth.service.generate_token", side_effect=[
             ("access123", "jti_access", 111),
             ("refresh123", "jti_refresh", 222),
         ]), \
         patch("src.auth.service.store_refresh_token_in_db", new_callable=AsyncMock, return_value=None):

        access, user, refresh = await service.login_with_github(request)

        assert access == "access123"
        assert refresh == "refresh123"
        assert user.email == "sam@example.com"
        assert user.username == "sam"

        repo.get_by_email.assert_awaited_once_with("sam@example.com")
        repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_with_github_error_param():
    scope = {"type": "http", "query_string": b"error=access_denied"}
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"error": "access_denied"})

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    with pytest.raises(HTTPException) as exc:
        await service.login_with_github(request)

    assert exc.value.status_code == 400
    assert "GitHub authentication failed" in exc.value.detail


@pytest.mark.asyncio
async def test_login_with_github_missing_params():
    scope = {"type": "http", "query_string": b"code=123"}
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"code": "123"})
    request._cookies = {}  # missing state & cookie

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    with pytest.raises(HTTPException) as exc:
        await service.login_with_github(request)

    assert exc.value.status_code == 400
    assert "Invalid OAuth callback" in exc.value.detail


@pytest.mark.asyncio
async def test_login_with_github_state_mismatch():
    scope = {
        "type": "http",
        "query_string": b"code=123&state=A"
    }
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"code": "123", "state": "A"})
    request._cookies = {"oauth_state_github": "B"}  # mismatch

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    with pytest.raises(HTTPException) as exc:
        await service.login_with_github(request)

    assert exc.value.status_code == 400
    assert "Invalid OAuth state" in exc.value.detail



@pytest.mark.asyncio
async def test_login_with_github_email_none():
    scope = {
        "type": "http",
        "query_string": b"code=valid&state=xyz"
    }
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"code": "valid", "state": "xyz"})
    request._cookies = {"oauth_state_github": "xyz"}

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    repo.get_by_email.return_value = None

    created_user = User(
        id=uuid4(),
        email="sam@github.local",
        username="sam",
        provider=Provider.GITHUB,
        is_verified=True
    )
    repo.create.return_value = created_user

    with patch("src.auth.utils.github_tokens", return_value="github_token"), \
         patch("src.auth.utils.get_github_user_info", return_value=(None, "sam")), \
         patch("src.auth.service.generate_token", side_effect=[
             ("access123", "jti_access", 111),
             ("refresh123", "jti_refresh", 222),
         ]), \
         patch("src.auth.service.store_refresh_token_in_db", new_callable=AsyncMock, return_value=None):

        access, user, refresh = await service.login_with_github(request)

        assert user.email == "sam@github.local"
        assert user.username == "sam"
        repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_with_github_existing_user():
    scope = {
        "type": "http",
        "query_string": b"code=valid&state=xyz"
    }
    request = StarletteRequest(scope)
    request._query_params = QueryParams({"code": "valid", "state": "xyz"})
    request._cookies = {"oauth_state_github": "xyz"}

    repo = AsyncMock()
    token_repo = AsyncMock()
    login_code_repo = AsyncMock()
    service = UserService(repo, token_repo, login_code_repo)

    existing_user = User(
        id=uuid4(),
        email="sam@example.com",
        username="sam",
        provider=Provider.GITHUB,
        is_verified=True
    )

    repo.get_by_email.return_value = existing_user

    with patch("src.auth.utils.github_tokens", return_value="token"), \
         patch("src.auth.utils.get_github_user_info", return_value=("sam@example.com", "sam")), \
         patch("src.auth.service.generate_token", side_effect=[
             ("access123", "jti_access", 111),
             ("refresh123", "jti_refresh", 222),
         ]), \
         patch("src.auth.service.store_refresh_token_in_db", new_callable=AsyncMock, return_value=None):

        access, user, refresh = await service.login_with_github(request)

        assert user == existing_user
        repo.create.assert_not_called()


