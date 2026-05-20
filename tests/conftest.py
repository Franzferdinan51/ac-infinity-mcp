import pytest


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("AC_INFINITY_EMAIL", "test@example.com")
    monkeypatch.setenv("AC_INFINITY_PASSWORD", "testpassword123")
