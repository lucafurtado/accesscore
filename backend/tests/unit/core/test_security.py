import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_password_is_not_plaintext() -> None:
    password = "correct-horse-battery-staple"

    hashed = hash_password(password)

    assert hashed != password


def test_verify_password_succeeds_for_correct_password() -> None:
    password = "correct-horse-battery-staple"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_fails_for_wrong_password() -> None:
    hashed = hash_password("correct-horse-battery-staple")

    assert verify_password("wrong-password", hashed) is False


def test_valid_access_token_decodes_with_expected_subject() -> None:
    user_id = uuid.uuid4()

    token = create_access_token(user_id)
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_expired_access_token_fails_to_decode() -> None:
    now = datetime.now(UTC)
    expired_claims = {
        "sub": str(uuid.uuid4()),
        "iat": now - timedelta(minutes=30),
        "exp": now - timedelta(minutes=15),
        "type": "access",
    }
    expired_token = jwt.encode(
        expired_claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(expired_token)


def test_tampered_access_token_fails_to_decode() -> None:
    token = create_access_token(uuid.uuid4())
    tampered_token = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")

    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered_token)


def test_refresh_tokens_are_random() -> None:
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second


def test_hash_refresh_token_is_deterministic() -> None:
    token = generate_refresh_token()

    assert hash_refresh_token(token) == hash_refresh_token(token)


def test_refresh_token_hash_differs_from_raw_token() -> None:
    token = generate_refresh_token()

    assert hash_refresh_token(token) != token
