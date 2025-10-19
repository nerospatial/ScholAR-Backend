
# ScholAR Backend API Documentation

## Authentication Endpoints (`/api/v1/auth`)

### 1. `POST /signup`

- **Request Body:** `UserCreate`
  - `email`: string (email)
  - `password`: string
  - `confirm_password`: string

- **Response:** 200 OK or error

---

### 2. `POST /verify`

- **Request Body:** `VerifyRequest`
  - `email`: string (email)
  - `code`: int (6 digits)

- **Response:** `VerifyResponse`
  - `access_token`: string
  - `refresh_token`: string
  - `expires_in`: int

---

### 3. `POST /resend`

- **Request Body:** `ResendRequest`
  - `email`: string (email)

- **Response:** `ResendResponse`
  - `status`: string
  - `message`: string
  - `cooldown_seconds`: int
  - `attempts_remaining`: int (optional)

---

### 4. `POST /login`

- **Request Body:** `UserLogin`
  - `email`: string (email)
  - `password`: string

- **Response:** 200 OK or error

---

### 5. `POST /forgot`

- **Request Body:** `ForgotPasswordRequest`
  - `email`: string (email)

- **Response:** `ForgotPasswordResponse`
  - `status`: string
  - `message`: string

---

### 6. `POST /reset`

- **Request Body:** `ResetPasswordRequest`
  - `email`: string (email)
  - `code`: int (6 digits)
  - `new_password`: string
  - `confirm_new_password`: string

- **Response:** `ResetPasswordResponse`
  - `status`: string
  - `message`: string

---

### 7. `POST /refresh`

- **Request Body:** `TokenRefreshRequest`
  - `refresh_token`: string

- **Response:** `TokenRefreshResponse`
  - `access_token`: string
  - `refresh_token`: string
  - `expires_in`: int

---

## Device Authentication Endpoints (`/api/v1/auth`) (on going...)


### 1. `POST /device/register`

- **Request Body:** `DeviceRegisterRequest`
  - `user_id`: str (uuid)

- **Response:** `DeviceRegisterResponse`
  - `registration_token`: int
  - `access_token`: str
  - `expires_in`: int

---

### 2. `POST /device/verify`

- **Headers:**
  - `Authorization: Bearer <access_token>`

- **Request Body:** `DeviceVerifyRequest`
  - `user_id`: str (uuid)
  - `registration_token`: int
  - `hardware_id`: str
  - `device_name`: str
  - `firmware_version`: str

- **Response:** `DeviceVerifyResponse`
  - `user_id`: str (uuid)
  - `access_token`: str
  - `refresh_token`: str
  - `expires_in`: int

---

### 3. `GET /device/get-devices`

- **Headers:**
  - `Authorization: Bearer <access_token>`

- **Request Body:** `UserDevicesRequest` (for OpenAPI/typed clients)
  - `user_id`: str (uuid)

- **Response:** `UserDevicesResponse`
  - `devices`: list of `DeviceInfo`

---

## Google Authentication Endpoints (`/api/v1/auth/google`)

### 1. `GET /login`

- **Response:** Redirect to Google OAuth

### 2. `GET /callback`

- **Response:** User info (see `GoogleUser` schema)

---

## User Profile Endpoint

### 1. `GET /me`

- **Headers:** `Authorization: Bearer <access_token>`

- **Response:** `UserProfile`
  - `id`: int
  - `email`: string
  - `username`: string (optional)
  - `is_verified`: bool
  - `auth_type`: string

---

## Data Types


### UserCreate

```python
email: EmailStr
password: str
confirm_password: str
```

### UserLogin

```python
email: EmailStr
password: str
```

### VerifyRequest

```python
email: EmailStr
code: int  # 6 digits
```

### VerifyResponse

```python
access_token: str
refresh_token: str
expires_in: int
```

### ResendRequest

```python
email: EmailStr
```

### ResendResponse

```python
status: str
message: str
cooldown_seconds: int
attempts_remaining: int 
```

### ForgotPasswordRequest

```python
email: EmailStr
```

### ResetPasswordRequest

```python
email: EmailStr
code: int  # 6 digits
new_password: str
confirm_new_password: str
```

### ForgotPasswordResponse / ResetPasswordResponse

```python
status: str
message: str
```

### TokenRefreshRequest

```python
refresh_token: str
```

### TokenRefreshResponse

```python
access_token: str
refresh_token: str
expires_in: int
```

### DeviceRegisterRequest

```python
user_id: str (uuid)
```

### DeviceRegisterResponse

```python
registration_token: int
access_token: str
expires_in: int
```


### DeviceVerifyRequest

```python
user_id: str (uuid)
registration_token: int
hardware_id: str
device_name: str
firmware_version: str
```


### DeviceVerifyResponse

```python
user_id: str (uuid)
access_token: str
refresh_token: str
expires_in: int
```

### GoogleUser

```python
google_sub: str
email: str
username: str
```

### UserProfile

```python
id: str (uuid)
email: str
username: str (optional)
is_verified: bool
auth_type: str
```
### DeviceInfo

```python
device_id: UUID
device_name: str
firmware_version: str
```

### UserDevicesRequest

```python
user_id: UUID
```

### UserDevicesResponse

```python
devices: List[DeviceInfo]

```