# Auth API Structure

Derived from the actual FastAPI auth routes and services in this project (`src/auth/router.py`).

## Endpoints

**POST /register -> Create a new local account**
- Auth required: no
- Query params:
  - none
- Path params:
  - none
- Headers:
  - none
- Request body (JSON):
  - email (string, EmailStr, required, user email)
  - username (string, required, unique handle)
  - password (string, required, 6-128 chars)
- Responses:
  - 201 Created — JSON: { id: UUID, email: string, username: string, provider: "local"|"google"|"github" }
  - 400 Bad Request — email or username already exists

**POST /login -> Password login and issue tokens**
- Auth required: no
- Query params:
  - none
- Path params:
  - none
- Headers:
  - none
- Request body (JSON):
  - email (string, EmailStr, required)
  - password (string, required, 6-128 chars)
- Responses:
  - 200 OK — JSON: { token: string, type: "Bearer", user: { id: UUID, email: string, username: string, provider: "local"|"google"|"github" } }; Set-Cookie refresh_token (HttpOnly, SameSite=lax, Secure=false, max-age 7d)
  - 401 Unauthorized — invalid email or password
  - 403 Forbidden — user disabled

**POST /refresh-token -> Rotate refresh token and issue new access token**
- Auth required: no (requires refresh_token cookie)
- Query params:
  - none
- Path params:
  - none
- Headers:
  - refresh_token cookie (required, HttpOnly)
- Request body (JSON):
  - none
- Responses:
  - 200 OK — JSON: { token: string, type: "Bearer" }; Set-Cookie refresh_token (rotated; HttpOnly, SameSite=lax, Secure=false, max-age 7d)
  - 401 Unauthorized — missing or invalid refresh token

**GET /verify -> Confirm email verification token**
- Auth required: no
- Query params:
  - token (string, required, email verification token)
- Path params:
  - none
- Headers:
  - none
- Request body (JSON):
  - none
- Responses:
  - 202 Accepted — JSON: { message: "Email is Verified" }
  - 202 Accepted — JSON: { message: "Email is already Verified" }

**POST /request/verify -> Resend verification email**
- Auth required: yes (Bearer access token; allows inactive/unverified users)
- Query params:
  - none
- Path params:
  - none
- Headers:
  - Authorization (required, Bearer access token)
- Request body (JSON):
  - none
- Responses:
  - 202 Accepted — JSON: { message: "New Verification Email has been sent" }
  - 202 Accepted — JSON: { message: "Email is already verified" }

**POST /forget-password -> Request password reset link**
- Auth required: no
- Query params:
  - none
- Path params:
  - none
- Headers:
  - none
- Request body (JSON):
  - email (string, EmailStr, required)
- Responses:
  - 202 Accepted — JSON: { message: "If an account with this email exists, a password reset link has been sent." }

**POST /new-password -> Set a new password using reset token**
- Auth required: no
- Query params:
  - none
- Path params:
  - none
- Headers:
  - none
- Request body (JSON):
  - token (string, required, reset/validation token)
  - password (string, required)
- Responses:
  - 202 Accepted — JSON: { message: "Password has been changed successfuly" }
  - 401 Unauthorized — invalid token or user not found

**POST /change-password -> Change password while authenticated**
- Auth required: yes (Bearer access token; user must be active and verified)
- Query params:
  - none
- Path params:
  - none
- Headers:
  - Authorization (required, Bearer access token)
- Request body (JSON):
  - old_password (string, required, 6-128 chars)
  - new_password (string, required, 6-128 chars)
- Responses:
  - 200 OK — JSON: { message: "Password has been changed successfuly" }
  - 403 Forbidden — old password incorrect or user inactive/unverified

**POST /request/login-code -> Send one-time login code to email**
- Auth required: no
- Query params:
  - none
- Path params:
  - none
- Headers:
  - none
- Request body (JSON):
  - email (string, EmailStr, required)
- Responses:
  - 200 OK — JSON: { message: "If an account with this email exists, a login code has been sent." }
  - 400 Bad Request — email not found

**POST /login/code -> Login with email + one-time code**
- Auth required: no
- Query params:
  - none
- Path params:
  - none
- Headers:
  - none
- Request body (JSON):
  - email (string, EmailStr, required)
  - code (string, required)
- Responses:
  - 200 OK — JSON: { token: string, type: "Bearer", user: { id: UUID, email: string, username: string, provider: "local"|"google"|"github" } }; Set-Cookie refresh_token (HttpOnly, SameSite=lax, Secure=false, max-age 7d)
  - 400 Bad Request — invalid or expired code/email
  - 403 Forbidden — user disabled

**GET /google/login -> Start Google OAuth login**
- Auth required: no
- Query params:
  - none
- Path params:
  - none
- Headers:
  - none
- Request body (JSON):
  - none
- Responses:
  - 307 Temporary Redirect — redirects to Google OAuth URL; Set-Cookie oauth_state_google (HttpOnly, Secure=true, SameSite=lax)

**GET /auth/social/callback/google -> Google OAuth callback**
- Auth required: no
- Query params:
  - code (string, required, OAuth code)
  - state (string, required, must match oauth_state_google cookie)
- Path params:
  - none
- Headers:
  - oauth_state_google cookie (required, HttpOnly)
- Request body (JSON):
  - none
- Responses:
  - 200 OK — JSON: { token: string, type: "Bearer", user: { id: UUID, email: string, username: string, provider: "local"|"google"|"github" } }; deletes oauth_state_google cookie; Set-Cookie refresh_token (HttpOnly, SameSite=lax, Secure=false, max-age 7d)
  - 400 Bad Request — invalid callback or state mismatch

**GET /github/login -> Start GitHub OAuth login**
- Auth required: no
- Query params:
  - none
- Path params:
  - none
- Headers:
  - none
- Request body (JSON):
  - none
- Responses:
  - 307 Temporary Redirect — redirects to GitHub OAuth URL; Set-Cookie oauth_state_github (HttpOnly, Secure=true, SameSite=lax)

**GET /auth/social/callback/github -> GitHub OAuth callback**
- Auth required: no
- Query params:
  - code (string, required, OAuth code)
  - state (string, required, must match oauth_state_github cookie)
  - error (string, optional, indicates GitHub authorization error)
- Path params:
  - none
- Headers:
  - oauth_state_github cookie (required, HttpOnly)
- Request body (JSON):
  - none
- Responses:
  - 200 OK — JSON: { token: string, type: "Bearer", user: { id: UUID, email: string, username: string, provider: "local"|"google"|"github" } }; deletes oauth_state_github cookie; Set-Cookie refresh_token (HttpOnly, SameSite=lax, Secure=false, max-age 7d)
  - 400 Bad Request — GitHub error, invalid callback, or state mismatch

**POST /deactivate -> Deactivate the authenticated user account**
- Auth required: yes (Bearer access token; user must be active and verified)
- Query params:
  - none
- Path params:
  - none
- Headers:
  - Authorization (required, Bearer access token)
- Request body (JSON):
  - none
- Responses:
  - 202 Accepted — JSON: { message: "User deactivated." }
