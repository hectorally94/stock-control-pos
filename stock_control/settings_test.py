"""
Test settings: run the suite on SQLite in-memory so tests never need a MySQL
server. Imports everything from the normal settings and overrides only the
database, cache, and session backends.

Used via pytest.ini (DJANGO_SETTINGS_MODULE = stock_control.settings_test).
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Faster, deterministic password hashing in tests.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
