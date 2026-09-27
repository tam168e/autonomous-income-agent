import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.providers.mysterium import MysteriumNodeProvider, _number, _token_human


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text=None):
        self._payload = payload
        self.status_code = status_code
        self.text = text if text is not None else ("" if payload is None else "payload")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method, url, headers=None, json=None):
        if method.upper() != "GET":
            return FakeResponse({}, status_code=405)
        return await self.get(url, headers=headers)

    async def get(self, url, headers=None):
        path = url.split("4449", 1)[-1]
        responses = {
            "/identities": FakeResponse(["identity-1"]),
            "/healthcheck": FakeResponse({"healthy": True}),
            "/identities/identity-1": FakeResponse(
                {"registrationStatus": "Registered", "balance": 2.5}
            ),
            "/services?includeAll=true": FakeResponse(
                [{"id": "service-1", "status": "running", "type": "residential"}]
            ),
            "/node/provider/activity-stats": FakeResponse(
                {"onlinePercent": 91}, status_code=503
            ),
            "/node/provider/quality": FakeResponse(
                {"quality": 93}, status_code=503
            ),
        }
        return responses.get(path, FakeResponse({}, status_code=404))


class MysteriumProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_optional_telemetry_failure_does_not_mark_provider_unhealthy(self):
        provider = MysteriumNodeProvider(confirmed_countries="Iran")

        with patch("app.providers.mysterium.httpx.AsyncClient", FakeAsyncClient):
            status = await provider.get_runtime_status()

        self.assertTrue(status["healthy"])
        self.assertEqual(status["activeServices"], 1)
        self.assertEqual(status["registrationStatus"], "Registered")
        self.assertEqual(status["onlinePercent"], 0.0)
        self.assertEqual(status["quality"], 0.0)
        self.assertFalse(status["activityTelemetryAvailable"])
        self.assertFalse(status["qualityTelemetryAvailable"])

    async def test_country_confirmation_is_required_before_eligibility(self):
        provider = MysteriumNodeProvider(confirmed_countries="")
        provider.get_runtime_status = AsyncMock(
            return_value={
                "healthy": True,
                "countryConfirmationRequired": True,
                "identityId": "identity-1",
                "registrationStatus": "Registered",
                "activeServices": 1,
                "supportedCountries": [],
            }
        )

        result = await provider.check_eligibility("Iran")
        self.assertEqual(result, "USER_ACTION_REQUIRED")

    async def test_withdrawal_checks_wallet_and_balance_before_dispatch(self):
        provider = MysteriumNodeProvider()
        provider.resolve_identity_id = AsyncMock(return_value="identity-1")
        provider._request = AsyncMock(
            side_effect=[
                {"balance": 10.0},
                {"amount": 2.0},
                {"address": "0x1111111111111111111111111111111111111111"},
                {"hermesId": "hermes-1"},
                {"ok": True},
            ]
        )

        result = await provider.request_withdrawal(
            4.0,
            {
                "address": "0x1111111111111111111111111111111111111111",
                "network": "POLYGON",
                "asset": "MYST",
            },
        )

        self.assertTrue(result["success"])
        self.assertIn("providerReference", result["data"])
        self.assertEqual(provider._request.await_count, 5)

    async def test_withdrawal_rejects_wrong_network_before_network_calls(self):
        provider = MysteriumNodeProvider()
        provider.resolve_identity_id = AsyncMock(return_value="identity-1")
        provider._request = AsyncMock()

        result = await provider.request_withdrawal(
            1.0,
            {
                "address": "0x1111111111111111111111111111111111111111",
                "network": "BSC",
                "asset": "MYST",
            },
        )

        self.assertFalse(result["success"])
        provider._request.assert_not_awaited()

    async def test_withdrawal_rejects_malformed_evm_address_before_network_calls(self):
        provider = MysteriumNodeProvider()
        provider.resolve_identity_id = AsyncMock(return_value="identity-1")
        provider._request = AsyncMock()

        result = await provider.request_withdrawal(
            1.0,
            {
                "address": "0xnot-a-wallet",
                "network": "POLYGON",
                "asset": "MYST",
            },
        )

        self.assertFalse(result["success"])
        provider._request.assert_not_awaited()

    def test_numeric_helpers_ignore_invalid_values(self):
        self.assertEqual(_number("not-a-number", None, float("nan"), 3.5), 3.5)
        self.assertEqual(_token_human({"human": "1.25"}), 1.25)


if __name__ == "__main__":
    unittest.main()
