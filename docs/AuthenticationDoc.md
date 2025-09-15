# ScholAR Auth Spec — Frontend-Driven Requirements (v1)

This document captures everything the Android app needs from the backend for **email+code verification auth** (login & signup), plus tokening, preflight, resend, and forgot password. It’s written to be directly actionable for the backend.

---

## High-level flow

### Signup

1. `POST /auth/signup` with `email + password` → **200** (send 6-digit code by email).
2. User enters code → `POST /auth/verify` → **200** with tokens.
3. App stores tokens → **Preflight** `GET /me` → returns user profile, flags (e.g., onboarding).
4. Navigate to Home.

### Login

1. `POST /auth/login` with `email + password` → **200** (send 6-digit code).
2. `POST /auth/verify` with `email + code` → **200** with tokens.
3. Store tokens → **Preflight** `GET /me` → go Home.

> Both login & signup go through the **same verification endpoint**. Codes must be one-time, short-lived.

---

## Entities & semantics

* **User**: identified by `email`.
* **Password**: provided only at signup/login, never after.
* **Verification code**: 6 digits, expires (configurable, 10 minutes expiry), one-time use, rate-limited resend.
* **Tokens**: `access_token` (JWT) + optional `refresh_token`.
* **Session**: Android persists tokens; email is stored (non-sensitive) for UX and resend/forgot flows.

---

## Endpoints

### 1) Signup — request verification code

**POST** `/auth/signup`

**Request**

```json
{
  "email": "user@example.com",
  "password": "S0m3Passw0rd!"
}
```

**Response**

* **200 OK**

```json
{
  "status": "ok",
  "message": "Verification code sent"
}
```

**Error cases**

```json
{
  "code": ERROR_CODE,
  "message": ERROR_MESSSAGE
}

```

* **409 Conflict**: email already registered.
* **400 Bad Request**: invalid email/password (min length, complexity).
* **429 Too Many Requests**: abuse protection. (3 in 30 mins)
* **5xx**: generic server error.

**Backend notes**

* Create user in a **pending/UNVERIFIED** state.
* Generate 6-digit numeric code; store hashed with TTL (e.g., 10 min).
* Send email with code; include rate limiting information in the email as well.

---

### 2) Login — request verification code

**POST** `/auth/login`

**Request**

```json
{
  "email": "user@example.com",
  "password": "S0m3Passw0rd!"
}
```

**Response**

* **200 OK**

```json
{
  "status": "ok",
  "message": "Verification code sent"
}
```

**Error cases**

```json
{
  "code": ERROR_CODE,
  "message": ERROR_MESSSAGE
}

```

* **401 Unauthorized**: wrong credentials.
* **404 Not Found**: user not found (or return 401 to avoid user enumeration (better approach)).
* **423 Locked**: account locked (optional). (Not needed right now)
* **429 Too Many Requests**: throttling.
* **5xx** Some Server Error.

**Backend notes**

* Only send code if password is correct.
* Code semantics same as signup.

---

### 3) Verify — exchange code for tokens

**POST** `/auth/verify`

**Request**

```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

**Response**

* **200 OK**

```json
{
  "accessToken": "eyJhbGciOi...",
  "refreshToken": "r1_aBc...",
  "expiresIn": 3600 
}
```

**Error cases**

```json
{
  "code": ERROR_CODE,
  "message": ERROR_MESSSAGE
}

```

* **400 Bad Request**: malformed.
* **401 Unauthorized**: invalid/expired code.
* **410 Gone**: code already used.
* **423 Locked**: too many failed attempts.
* **429 Too Many Requests**: throttling.
* **5xx**.

**Backend notes**

* On success:

  * Mark user as VERIFIED (if signup).
  * Invalidate the code (one-time use).
  * Issue tokens (access \[+ refresh]).
* Consider returning `firstTime` or include in `/me`.

---

### 4) Resend verification code

**POST** `/auth/resend`

**Request**

```json
{
  "email": "user@example.com"
}
```

**Response**

* **200 OK**

```json
{
  "status": "ok",
  "message": "Verification code resent",
  "cooldownSeconds": 60
}
```

**Error cases**

* **404/400** if user not in a state that expects a code.
* **429** if within cooldown or rate limits exceeded.

**Backend notes**

* Enforce per-email resend cooldown (e.g., 60s) and per-day cap (e.g., 10).
* Replace any prior code with a new one (invalidate old).

---

### 5) Forgot password — request reset code

**POST** `/auth/forgot`

**Request**

```json
{
  "email": "user@example.com"
}
```

**Response**

* **200 OK** (don’t reveal if user exists)

```json
{
  "status": "ok",
  "message": "If an account exists, a reset email has been sent."
}
```

**Backend notes**

* Email a 6-digit code.
* add: `POST /auth/reset` to set new password:

  * **POST** `/auth/reset`

    ```json
    { "email": "user@example.com", "code": "654321", "newPassword": "..." }
    ```
  * **200 OK** or **401/410/429** accordingly.

---

### 6) Preflight — get current user profile

**GET** `/me`

**Headers**

```
Authorization: Bearer <access_token>
```

**Response**

* **200 OK**

```json
{
  "id": "u_123",
  "email": "user@example.com",
  "name": "Ada Lovelace",
  "firstTime": true/false,
  "roles": [
    "user"
  ],
  "updatedAt": "2025-09-01T12:30:00Z"
}
```

**Error cases**

* **401 Unauthorized**: invalid/expired token → client triggers refresh or logout.
* **5xx**.

**Backend notes**

* Minimal payload; fast path; ideal for bootstrap.

---

### 7) Token refresh

**POST** `/auth/refresh`

**Request**

```json
{
  "refreshToken": "r1_aBc..."
}
```

**Response**

* **200 OK**

```json
{
  "accessToken": "newAccess...",
  "refreshToken": "newRefresh...",   // rotation
  "expiresIn": 3600
}
```

**Error cases**

* **401** invalid/expired refresh → logout client.
* **429** (abuse protection).
* **5xx**.

**Backend notes**

* Support refresh token rotation.
* Consider revocation list.

---

## Status codes summary

* **200** Success (login/signup/verify/resend/forgot/me/refresh)
* **400** Validation errors (bad email/password format, malformed JSON)
* **401** Auth failures (wrong creds, invalid code, invalid token)
* **404** Resource not found (optional for non-enumeration)
* **409** Conflict (signup with existing email)
* **410** Gone (code already used/expired)
* **423** Locked (too many attempts)
* **429** Rate limited
* **5xx** Server errors

Return a consistent JSON error shape, e.g.:

```json
{
  "error": "invalid_code",
  "message": "The verification code is invalid or expired"
}
```

---

## Validation & rules

* **Email:** RFC-ish format; treat case-insensitively; normalize to lowercase server-side.
* **Password:** configurable policy; return a generic message on failure (avoid leaking policy specifics if desired).
* **Code:** exactly **6 digits**, numeric, one-time, TTL (e.g., 10 min).
* **Resend:** enforce cooldown (e.g., 60s) + daily cap.
* **Lockouts:** optional after N failed attempts; return `423 Locked` with retry-after header.

---

## Security & privacy

* Never return whether an email exists from unauthenticated endpoints (`/auth/forgot` should be generic).
* Store verification codes hashed; never persist raw.
* Tokens should be signed (JWT) or opaque and verifiable server-side.
* Support token **refresh**; short access token TTL (e.g., 1h).
* Consider IP/device based abuse throttles for resend/login attempts.
* Audit log (optional): verification sends, attempts, lockouts.

---

## Email templates (backend-owned)

* **Subject (signup/login):** `Your ScholAR verification code`
* **Body:** “Your code is **123456**. It expires in 10 minutes. If you didn’t request this, ignore.”
* Include **support contact** footer and **rate limit** info if blocked.

---

## OpenAPI sketch (names only)

* `POST /auth/signup` — `SignupRequest`, empty success body or `{status}`
* `POST /auth/login` — `LoginRequest`, empty success body or `{status}`
* `POST /auth/verify` — `VerifyRequest` → `TokenResponse`
* `POST /auth/resend` — `ResendRequest` (email) → `{status, cooldownSeconds}`
* `POST /auth/forgot` — `ForgotRequest` (email) → generic `{status}`
* `POST /auth/reset` — `ResetRequest` (email, code, newPassword) → `{status}`
* `GET /me` — `MeResponse`
* `POST /auth/refresh` — `RefreshRequest` → `TokenResponse`

---

## Android expectations (so backend can optimize)

* The app stores `email` in a local store to reuse across flows (resend/forgot).
* The app expects **deterministic errors** (401/410/429/etc.) to render clear messages.
* After `verify`, app immediately calls **`/me`** to bootstrap.
* On any 401 from `/me`, app will attempt **refresh** once, then logout on failure.
* Resend button is disabled for the cooldown the server returns.
* All times expected in **UTC** with ISO 8601 when relevant.

---

## Examples (happy path)

**Signup**

1. `/auth/signup` → 200
2. `/auth/verify` → 200 `{accessToken, refreshToken, expiresIn, firstTime:true}`
3. `/me` → `{..., onboardingComplete:false}`
4. Client navigates to Onboarding.

**Login**

1. `/auth/login` → 200
2. `/auth/verify` → 200 `{accessToken, refreshToken, expiresIn}`
3. `/me` → `{..., onboardingComplete:true}`
4. Client navigates Home.

---

## Nice-to-haves (not blocking)

* Include `retryAfterSeconds` in 429 responses.
* Include `attemptsRemaining` when near lockout.
* Optional device metadata in requests for analytics/fraud (platform, app version).

---