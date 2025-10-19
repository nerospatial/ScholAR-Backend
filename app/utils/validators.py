import re
from typing import Tuple

def validate_email(email: str) -> Tuple[bool, str]:
    email = email.lower().strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, "Email is valid"

def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password meets security requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    return True, "Password is valid"

def validate_passwords_match(password: str, confirm_password: str) -> Tuple[bool, str]:
    """Validate that password and confirmation password match"""
    if password != confirm_password:
        return False, "Passwords do not match"
    return True, "Passwords match"
