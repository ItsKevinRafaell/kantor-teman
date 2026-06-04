"""Security tests - rate limiting, token validation, encryption."""
import time
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.dependencies import (
    _login_attempts, _login_locked_until,
    hash_password, verify_password, encrypt_password, decrypt_password,
    create_token, _record_login_failure,
    LOGIN_RATE_MAX, LOGIN_LOCKOUT_SECONDS,
)
from models import User


class TestLoginRateLimit:
    """Test login rate limiting - 5 failed attempts = 15 min lockout."""

    def test_login_rate_limit_after_5_failures(self, client, db):
        """Verify 5 failed login attempts triggers 15-minute lockout."""
        # Clear any existing rate limit state
        _login_attempts.clear()
        _login_locked_until.clear()
        test_ip = "192.168.99.99"

        # Check if user exists, if not create
        user = db.query(User).filter(User.email == "ratetest@test.com").first()
        if not user:
            user = User(
                name="Rate Test",
                email="ratetest@test.com",
                hashed_password=hash_password("correct-password"),
                role="user",
            )
            db.add(user)
            db.commit()
        else:
            # Update password to known value
            user.hashed_password = hash_password("correct-password")
            db.commit()

        # Attempt 5 failed logins
        for i in range(LOGIN_RATE_MAX):
            response = client.post(
                "/api/auth/login",
                json={"email": "ratetest@test.com", "password": "wrong-password"},
            )
            assert response.status_code == 401, f"Attempt {i+1} should fail"

        # 6th attempt should be rate limited (429)
        response = client.post(
            "/api/auth/login",
            json={"email": "ratetest@test.com", "password": "wrong-password"},
        )
        assert response.status_code == 429, "Should be rate limited after 5 failures"
        assert "Terlalu banyak percobaan" in response.json()["detail"]
        assert "Retry-After" in response.headers

    def test_login_rate_limit_lockout_duration(self, client, db):
        """Verify lockout lasts for 15 minutes (900 seconds)."""
        _login_attempts.clear()
        _login_locked_until.clear()

        # Trigger lockout via direct function call
        test_ip = "10.99.88.77"
        _login_attempts.clear()
        _login_locked_until.clear()
        for _ in range(LOGIN_RATE_MAX):
            _record_login_failure(test_ip)

        lockout_end = _login_locked_until.get(test_ip)
        assert lockout_end is not None, "Lockout should be recorded"
        lockout_duration = lockout_end - time.time()
        assert abs(lockout_duration - LOGIN_LOCKOUT_SECONDS) < 5, \
            f"Lockout should be {LOGIN_LOCKOUT_SECONDS}s, got {lockout_duration}s"

    def test_login_success_resets_counter(self, client, db):
        """Verify successful login resets the failure counter."""
        _login_attempts.clear()
        _login_locked_until.clear()
        test_ip = "10.0.0.50"

        # Ensure user exists
        user = db.query(User).filter(User.email == "reset@test.com").first()
        if not user:
            user = User(
                name="Reset Test",
                email="reset@test.com",
                hashed_password=hash_password("correct-password"),
                role="user",
            )
            db.add(user)
            db.commit()
        else:
            user.hashed_password = hash_password("correct-password")
            db.commit()

        # 3 failed attempts
        for _ in range(3):
            client.post(
                "/api/auth/login",
                json={"email": "reset@test.com", "password": "wrong"},
            )

        # Successful login should reset
        response = client.post(
            "/api/auth/login",
            json={"email": "reset@test.com", "password": "correct-password"},
        )
        assert response.status_code == 200

        # Counter should be cleared
        assert test_ip not in _login_attempts or len(_login_attempts.get(test_ip, [])) == 0


class TestTokenValidation:
    """Test JWT token validation."""

    def test_expired_token_returns_401(self, client, db):
        """Verify expired token returns 401."""
        import jwt as _jwt
        from datetime import datetime, timedelta, timezone

        # Create an expired token manually
        expired_payload = {
            "sub": "999",
            "email": "expired@test.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = _jwt.encode(
            expired_payload,
            os.environ["JWT_SECRET"],
            algorithm="HS256"
        )

        response = client.get(
            "/api/user/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
        assert "kadaluarsa" in response.json()["detail"].lower() or "token" in response.json()["detail"].lower()

    def test_invalid_token_returns_401(self, client, db):
        """Verify invalid token returns 401."""
        invalid_token = "invalid.token.here"
        response = client.get(
            "/api/user/me",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )
        assert response.status_code == 401

    def test_missing_token_returns_401(self, client, db):
        """Verify missing token returns 401."""
        response = client.get("/api/user/me")
        assert response.status_code == 401

    def test_valid_token_accepted(self, client, db):
        """Verify valid token is accepted."""
        email = "validtoken@test.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name="Valid Token Test",
                email=email,
                hashed_password=hash_password("test123"),
                role="user",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_token(user.id, user.email)

        response = client.get(
            "/api/user/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user.id
        assert data["email"] == user.email


class TestPasswordEncryption:
    """Test password encryption/decryption roundtrip."""

    def test_password_encryption_roundtrip(self):
        """Verify encrypt -> decrypt returns original password."""
        original_password = "MySecretPassword123!"
        encrypted = encrypt_password(original_password)
        assert encrypted != original_password
        decrypted = decrypt_password(encrypted)
        assert decrypted == original_password

    def test_different_passwords_encrypt_differently(self):
        """Verify different passwords produce different ciphertexts."""
        encrypted1 = encrypt_password("password-one")
        encrypted2 = encrypt_password("password-two")
        assert encrypted1 != encrypted2

    def test_bcrypt_hash_verification(self):
        """Verify bcrypt hash and verify work correctly."""
        password = "secure-password-123"
        hashed = hash_password(password)
        assert verify_password(password, hashed)
        assert not verify_password("wrong-password", hashed)


class TestAdminOnlyEndpoints:
    """Test admin-only endpoint access control."""

    def test_admin_endpoints_for_admin_user(self, client, db):
        """Verify admin user can access admin endpoints."""
        email = "adminendpoint@test.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name="Admin Endpoint Test",
                email=email,
                hashed_password=hash_password("admin123"),
                role="admin",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_token(user.id, user.email)
        response = client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_admin_endpoints_for_regular_user_returns_403(self, client, db):
        """Verify non-admin user gets 403 on admin endpoints."""
        email = "regularadmin@test.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name="Regular Admin Test",
                email=email,
                hashed_password=hash_password("user123"),
                role="user",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_token(user.id, user.email)
        response = client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    def test_wallet_endpoints_require_admin(self, client, db):
        """Verify wallet endpoints require admin role."""
        email = "wallettest@test.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name="Wallet Test User",
                email=email,
                hashed_password=hash_password("user123"),
                role="user",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_token(user.id, user.email)
        response = client.get(
            "/api/finance/wallets",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_regular_user_can_access_own_profile(self, client, db):
        """Verify regular user can access their own profile."""
        email = "profiletest@test.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name="Profile Test User",
                email=email,
                hashed_password=hash_password("user123"),
                role="user",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_token(user.id, user.email)
        response = client.get(
            "/api/user/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == user.email
