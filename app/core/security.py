"""
app/core/security.py
Security utilities: Password hashing and JWT management.
Decoupled from FastAPI dependencies to avoid circular imports.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from app.core.config import settings

# =============================================================================
# PASSWORD HASHING SETUP
# =============================================================================
# Using Argon2 as primary, with support for legacy hashes
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    # Tuning Argon2 based on .env settings (if you want tight control)
    argon2__time_cost=4, 
    argon2__memory_cost=1048576, # 1GB
    argon2__parallelism=8,
)

class SecurityManager:
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plaintext password using Argon2id (via passlib)
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against stored hash.
        Supports automatic upgrade of legacy hashes if passlib is configured so.
        """
        # Custom fallback for the specific manual sha256 implementation seen in old code
        if hashed_password.startswith("sha256$"):
            import hashlib
            parts = hashed_password.split("$")
            if len(parts) != 3:
                return False
            _, salt, stored_hash = parts
            computed = hashlib.sha256((plain_password + salt).encode()).hexdigest()
            return computed == stored_hash
        
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        Expects 'data' to contain 'sub' (user_id) and 'role'.
        """
        to_encode = data.copy()
        
        # Determine expiration
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        # Add standard JWT claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        })
        
        # Encode
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token.
        Returns: Dict containing 'user_id' and 'role'.
        Raises: HTTPException if invalid/expired.
        """
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            # Standard JWT uses 'sub' for Subject (User ID)
            user_id: str = payload.get("sub")
            role: str = payload.get("role")
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Invalid token: missing subject"
                )
            
            return {"user_id": user_id, "role": role}
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token"
            )
