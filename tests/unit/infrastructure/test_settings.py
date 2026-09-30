import pytest
from pydantic import ValidationError

from ecommerce_store_payments.infrastructure.config.settings import Settings


@pytest.mark.parametrize(
    "override",
    [
        {"environment": "unknown"},
        {"app_name": ""},
        {"mongodb_connection_string": "http://localhost:27017"},
        {"mongodb_connection_string": "mongodb://"},
        {"mongodb_connection_string": "mongodb://:27017"},
        {"mongodb_database_name": ""},
        {"mongodb_database_name": "../other"},
        {"mongodb_payments_collection_name": "system.payments"},
        {"mongodb_payment_history_collection_name": "system.history"},
        {"mongodb_probe_timeout_seconds": 0},
        {"mongodb_probe_timeout_seconds": 31},
        {"mongodb_server_selection_timeout_ms": 0},
        {"orders_api_base_url": "ftp://localhost:5000"},
        {"orders_api_base_url": "http://"},
        {"orders_api_base_url": "http://localhost:bad"},
        {"orders_api_timeout_seconds": 0},
        {"orders_api_timeout_seconds": 31},
        {"stripe_enabled": True},
        {"stripe_secret_key": "sk_live_fixture"},
        {"stripe_secret_key": "pk_test_fixture"},
        {"stripe_secret_key": "sk_test_"},
        {"stripe_secret_key": "sk_test_fixture space"},
        {"stripe_timeout_seconds": 0},
        {"stripe_timeout_seconds": 16},
        {"stripe_success_url": "https://user:password@example.org/orders"},
        {"stripe_success_url": "http://example.org/orders"},
        {"stripe_cancel_url": "https://example.org/orders#cancel"},
        {"stripe_cancel_url": "javascript:alert(1)"},
        {"stripe_success_url": "https://example.org:bad/orders"},
        {"stripe_success_url": "https://example.org:0/orders"},
    ],
)
def test_rejects_invalid_configuration(override: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(override)


def test_accepts_explicit_bounded_connection_settings() -> None:
    settings = Settings(
        environment="production",
        mongodb_connection_string="mongodb+srv://example.org/payments",
        mongodb_database_name="payments_prod",
        mongodb_payments_collection_name="payments",
        mongodb_probe_timeout_seconds=1.5,
        mongodb_server_selection_timeout_ms=1000,
        orders_api_base_url="https://orders.example.org",
    )

    assert settings.mongodb_probe_timeout_seconds == 1.5
    assert settings.mongodb_server_selection_timeout_ms == 1000
    assert settings.orders_api_timeout_seconds == 5.0


def test_stripe_secret_is_redacted_and_fixed_https_destinations_are_accepted() -> None:
    settings = Settings.model_validate(
        {
            "stripe_enabled": True,
            "stripe_secret_key": "sk_test_fixture",
            "stripe_success_url": "https://store.example.org/orders?checkout=success",
            "stripe_cancel_url": "https://store.example.org/orders?checkout=cancel",
        }
    )
    assert "sk_test_fixture" not in repr(settings)
    assert settings.stripe_enabled
