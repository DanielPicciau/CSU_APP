"""
Encrypted model fields for at-rest data protection.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


def _normalize_key(key: str | bytes) -> bytes:
    if isinstance(key, bytes):
        return key
    return key.encode()


@lru_cache
def _get_fernet() -> MultiFernet:
    keys = getattr(settings, "FERNET_KEYS", None)
    if not keys:
        raise ImproperlyConfigured("FERNET_KEYS is not configured")
    if isinstance(keys, str):
        keys = [keys]
    normalized = [_normalize_key(key) for key in keys]
    return MultiFernet([Fernet(key) for key in normalized])


class EncryptedFieldMixin:
    """Mixin providing Fernet encryption helpers."""

    def _encrypt(self, value: str) -> str:
        return _get_fernet().encrypt(value.encode()).decode()

    def _decrypt(self, value: str | bytes | Any) -> str:
        token = value if isinstance(value, bytes) else str(value).encode()
        return _get_fernet().decrypt(token).decode()


class EncryptedCharField(EncryptedFieldMixin, models.CharField):
    """Encrypted CharField stored as text in the database."""

    def db_type(self, connection) -> str:  # type: ignore[override]
        return models.TextField().db_type(connection)

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return self._encrypt(str(value))

    def from_db_value(self, value: Any, expression, connection) -> Any:
        if value in (None, ""):
            return value
        try:
            return self._decrypt(value)
        except InvalidToken:
            return value


class EncryptedTextField(EncryptedFieldMixin, models.TextField):
    """Encrypted TextField stored as text in the database."""

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return self._encrypt(str(value))

    def from_db_value(self, value: Any, expression, connection) -> Any:
        if value in (None, ""):
            return value
        try:
            return self._decrypt(value)
        except InvalidToken:
            return value


class EncryptedDateField(EncryptedFieldMixin, models.DateField):
    """Encrypted DateField stored as text in the database."""

    def db_type(self, connection) -> str:  # type: ignore[override]
        return models.TextField().db_type(connection)

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return self._encrypt(str(value))

    def from_db_value(self, value: Any, expression, connection) -> Any:
        if value in (None, ""):
            return value
        try:
            decrypted = self._decrypt(value)
            return super().to_python(decrypted)
        except InvalidToken:
            return super().to_python(value)


class EncryptedIntegerField(EncryptedFieldMixin, models.IntegerField):
    """Encrypted IntegerField stored as text in the database."""

    def db_type(self, connection) -> str:  # type: ignore[override]
        return models.TextField().db_type(connection)

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return self._encrypt(str(value))

    def from_db_value(self, value: Any, expression, connection) -> Any:
        if value in (None, ""):
            return value
        try:
            decrypted = self._decrypt(value)
            return super().to_python(decrypted)
        except InvalidToken:
            return super().to_python(value)


class EncryptedDateTimeField(EncryptedFieldMixin, models.DateTimeField):
    """Encrypted DateTimeField stored as text in the database."""

    def db_type(self, connection) -> str:  # type: ignore[override]
        return models.TextField().db_type(connection)

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return self._encrypt(str(value))

    def from_db_value(self, value: Any, expression, connection) -> Any:
        if value in (None, ""):
            return value
        try:
            decrypted = self._decrypt(value)
            return super().to_python(decrypted)
        except InvalidToken:
            return super().to_python(value)
