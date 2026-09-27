import asyncio
import base64
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx


PROVIDER_ID = "mysterium-node"
PROVIDER_NAME = "Mysterium Node"
OFFICIAL_SOURCE = (
    "https://help.mystnodes.com/en/articles/8005144-where-do-i-check-and-withdraw-my-earnings"
)


def _csv(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _number(*values: Any) -> float:
    for value in values:
        try:
            parsed = float(value)
            if parsed == parsed:
                return parsed
        except (TypeError, ValueError):
            continue
    return 0.0


def _is_evm_address(value: str) -> bool:
    return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}", str(value or "")))


def _token_human(value: Any) -> float:
    if isinstance(value, dict):
        return _number(value.get("human"), value.get("ether"))
    return _number(value)


class MysteriumNodeProvider:
    id = PROVIDER_ID
    name = PROVIDER_NAME
    execution_mode = "PERSISTENT"
    production_ready = True
    official_api_available = True
    requires_kyc = False
    requires_capital = False
    automation_allowed = True
    supported_currencies = ["MYST"]
    supported_networks = ["POLYGON"]
    minimum_withdrawal_usd = 0.0
    risk_level = "MEDIUM"

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        identity_id: str | None = None,
        confirmed_countries: str | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("MYSTERIUM_TEQUILAPI_URL")
            or "http://127.0.0.1:4449"
        ).rstrip("/")
        self.username = username or os.getenv("MYSTERIUM_TEQUILAPI_USER", "myst")
        self.password = password or os.getenv("MYSTERIUM_TEQUILAPI_PASSWORD", "mystberry")
        self.identity_id = (identity_id or os.getenv("MYSTERIUM_IDENTITY", "")).strip()
        self.supported_countries = _csv(
            confirmed_countries
            if confirmed_countries is not None
            else os.getenv("MYSTERIUM_CONFIRMED_COUNTRIES", "")
        )
        self.timeout = float(os.getenv("MYSTERIUM_API_TIMEOUT_SECONDS", "5"))

    def _headers(self) -> dict[str, str]:
        token = base64.b64encode(
            f"{self.username}:{self.password}".encode("utf-8")
        ).decode("ascii")
        return {
            "Accept": "application/json",
            "Authorization": "Basic " + token,
        }

    async def _request(
        self,
        path: str,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                self.base_url + path,
                headers={
                    **self._headers(),
                    **({"Content-Type": "application/json"} if payload is not None else {}),
                },
                json=payload,
            )
            raw = response.text
            try:
                body: Any = response.json() if raw else None
            except ValueError:
                body = raw
            if response.status_code >= 400:
                detail = body.get("message") if isinstance(body, dict) else body
                raise RuntimeError(
                    f"Mysterium API {response.status_code}: {detail or 'no response body'}"
                )
            return body

    async def resolve_identity_id(self) -> str:
        if self.identity_id:
            return self.identity_id

        response = await self._request("/identities")
        identities = (
            response
            if isinstance(response, list)
            else response.get("identities", [])
            if isinstance(response, dict)
            else []
        )
        first = identities[0] if identities else None
        identity_id = first if isinstance(first, str) else first.get("id") if isinstance(first, dict) else None
        if not identity_id:
            raise RuntimeError("Mysterium node has no local identity")
        self.identity_id = str(identity_id)
        return self.identity_id

    async def snapshot(self) -> dict[str, Any]:
        identity_id = await self.resolve_identity_id()
        health, identity, services, activity, quality = await _gather_snapshot(self, identity_id)
        service_list = services if isinstance(services, list) else []
        active_services = [
            service for service in service_list
            if (
                isinstance(service, dict)
                and str(service.get("status", "")).strip().lower() == "running"
            )
        ]
        return {
            "identityId": identity_id,
            "health": health,
            "identity": identity,
            "services": service_list,
            "activeServices": active_services,
            "activity": activity,
            "quality": quality,
        }

    async def get_runtime_status(self) -> dict[str, Any]:
        try:
            snapshot = await self.snapshot()
            return {
                "providerId": self.id,
                "healthy": True,
                "identityId": snapshot["identityId"],
                "registrationStatus": (
                    snapshot["identity"].get("registrationStatus")
                    if isinstance(snapshot["identity"], dict)
                    else "Unknown"
                ),
                "activeServices": len(snapshot["activeServices"]),
                "balanceMyst": _token_human(
                    snapshot["identity"].get("balanceTokens", snapshot["identity"].get("balance", 0))
                    if isinstance(snapshot["identity"], dict)
                    else 0
                ),
                "earningsTotalMyst": _token_human(
                    snapshot["identity"].get(
                        "earningsTotalTokens",
                        snapshot["identity"].get("earningsTotal", 0),
                    )
                    if isinstance(snapshot["identity"], dict)
                    else 0
                ),
                "quality": _number(
                    snapshot["quality"].get("quality")
                    if isinstance(snapshot["quality"], dict)
                    else 0
                ),
                "onlinePercent": _number(
                    snapshot["activity"].get("onlinePercent")
                    if isinstance(snapshot["activity"], dict)
                    else 0
                ),
                "activityTelemetryAvailable": isinstance(snapshot["activity"], dict)
                and snapshot["activity"].get("telemetryAvailable", True) is not False,
                "qualityTelemetryAvailable": isinstance(snapshot["quality"], dict)
                and snapshot["quality"].get("telemetryAvailable", True) is not False,
                "supportedCountries": self.supported_countries,
                "countryConfirmationRequired": not bool(self.supported_countries),
            }
        except Exception as exc:
            return {
                "providerId": self.id,
                "healthy": False,
                "error": str(exc),
                "supportedCountries": self.supported_countries,
                "countryConfirmationRequired": not bool(self.supported_countries),
            }

    async def check_eligibility(self, country: str) -> str:
        normalized = str(country).strip().lower()
        confirmed = [item.lower() for item in self.supported_countries]
        if normalized not in confirmed and "*" not in confirmed:
            return "USER_ACTION_REQUIRED"

        status = await self.get_runtime_status()
        if not status["healthy"]:
            return "USER_ACTION_REQUIRED"
        if status["countryConfirmationRequired"]:
            return "USER_ACTION_REQUIRED"
        if status.get("registrationStatus") != "Registered":
            return "USER_ACTION_REQUIRED"
        if status["activeServices"] == 0:
            return "USER_ACTION_REQUIRED"
        return "ELIGIBLE"

    async def discover(self, country: str) -> list[dict[str, Any]]:
        if await self.check_eligibility(country) != "ELIGIBLE":
            return []

        snapshot = await self.snapshot()
        balance = _token_human(
            snapshot["identity"].get("balanceTokens", snapshot["identity"].get("balance", 0))
            if isinstance(snapshot["identity"], dict)
            else 0
        )
        total = _token_human(
            snapshot["identity"].get(
                "earningsTotalTokens",
                snapshot["identity"].get("earningsTotal", 0),
            )
            if isinstance(snapshot["identity"], dict)
            else 0
        )
        quality = _number(
            snapshot["quality"].get("quality")
            if isinstance(snapshot["quality"], dict)
            else 0
        )
        online = _number(
            snapshot["activity"].get("onlinePercent")
            if isinstance(snapshot["activity"], dict)
            else 0
        )
        risk = "LOW" if quality >= 90 else "MEDIUM" if quality >= 70 else "HIGH"
        return [{
            "id": f"{self.id}:{snapshot['identityId']}",
            "providerId": self.id,
            "name": f"{self.name} ({snapshot['identityId'][:10]}…)",
            "description": (
                "Persistent Mysterium node income. "
                f"{len(snapshot['activeServices'])} provider service(s) are running; "
                f"verified balance is {balance:.6f} MYST. "
                "Income is produced by real network sessions, not by the application UI."
            ),
            "estimatedHourlyUsd": 0.0,
            "feeUsd": 0.0,
            "minimumWithdrawalUsd": 0.0,
            "requiresCapital": False,
            "requiresKyc": False,
            "automationAllowed": True,
            "supportedCountries": list(self.supported_countries),
            "riskLevel": risk,
            "eligibilityStatus": "ELIGIBLE",
            "sourceUrl": OFFICIAL_SOURCE,
            "lastVerifiedAt": datetime.now(timezone.utc).isoformat(),
            "score": 0.0,
            "metadata": {
                "executionMode": "PERSISTENT",
                "identityId": snapshot["identityId"],
                "balanceMyst": balance,
                "earningsTotalMyst": total,
                "quality": quality,
                "onlinePercent": online,
                "activeServices": [
                    {
                        "id": service.get("id"),
                        "type": service.get("type"),
                        "status": service.get("status"),
                    }
                    for service in snapshot["activeServices"]
                ],
            },
        }]

    async def verify_payment(self, payment_id: str, opportunity: dict[str, Any]) -> dict[str, Any]:
        if not payment_id:
            return {"success": False, "error": "A settlement transaction hash is required."}
        if not isinstance(opportunity, dict) or opportunity.get("providerId") != self.id:
            return {"success": False, "error": "Opportunity/provider association is invalid."}

        identity_id = await self.resolve_identity_id()
        if opportunity.get("id") != f"{self.id}:{identity_id}":
            return {"success": False, "error": "Opportunity does not belong to the configured Mysterium identity."}

        history = await self._request(
            "/transactor/settle/history?providerId=" + identity_id
        )
        settlements = (
            history
            if isinstance(history, list)
            else history.get("items", [])
            if isinstance(history, dict)
            else []
        )
        match = next(
            (
                item
                for item in settlements
                if isinstance(item, dict)
                and item.get("isWithdrawal") is not True
                and str(item.get("txHash", "")).lower() == payment_id.strip().lower()
            ),
            None,
        )
        if not match:
            return {"success": False, "error": "No matching Mysterium settlement was found."}

        rate_data = await self._request("/exchange/myst/usd")
        usd_per_myst = _number(
            rate_data.get("amount") if isinstance(rate_data, dict) else 0,
            rate_data.get("value") if isinstance(rate_data, dict) else 0,
            rate_data.get("rate") if isinstance(rate_data, dict) else 0,
            rate_data.get("price") if isinstance(rate_data, dict) else 0,
        )
        gross_myst = _number(match.get("amount"))
        fee_myst = _number(match.get("fees"))
        if not (usd_per_myst > 0 and gross_myst > 0 and 0 <= fee_myst <= gross_myst):
            return {"success": False, "error": "Settlement amount/fee/rate validation failed."}

        gross_usd = round(gross_myst * usd_per_myst, 8)
        fee_usd = round(fee_myst * usd_per_myst, 8)
        return {
            "success": True,
            "data": {
                "paymentId": str(match["txHash"]),
                "opportunityId": opportunity["id"],
                "providerId": self.id,
                "grossUsd": gross_usd,
                "feeUsd": fee_usd,
                "netUsd": round(gross_usd - fee_usd, 8),
                "evidenceType": "PROVIDER_API",
                "verifiedAt": match.get("settledAt") or datetime.now(timezone.utc).isoformat(),
            },
        }

    async def request_withdrawal(self, amount_usd: float, wallet: dict[str, Any]) -> dict[str, Any]:
        try:
            requested_usd = float(amount_usd)
        except (TypeError, ValueError):
            return {"success": False, "error": "Withdrawal amount must be numeric."}

        if requested_usd <= 0:
            return {"success": False, "error": "Withdrawal amount must be greater than zero."}
        if not isinstance(wallet, dict):
            return {"success": False, "error": "Wallet destination is required."}

        address = str(wallet.get("address", ""))
        if str(wallet.get("network", "")).upper() != "POLYGON" or str(wallet.get("asset", "")).upper() != "MYST":
            return {"success": False, "error": "Mysterium withdrawals require POLYGON / MYST."}
        if not _is_evm_address(address):
            return {"success": False, "error": "A valid EVM wallet address is required."}

        identity_id = await self.resolve_identity_id()
        identity = await self._request("/identities/" + identity_id)
        balance = _token_human(
            identity.get("balanceTokens", identity.get("balance", 0))
            if isinstance(identity, dict)
            else 0
        )
        rate_data = await self._request("/exchange/myst/usd")
        rate = _number(
            rate_data.get("amount") if isinstance(rate_data, dict) else 0,
            rate_data.get("value") if isinstance(rate_data, dict) else 0,
            rate_data.get("rate") if isinstance(rate_data, dict) else 0,
            rate_data.get("price") if isinstance(rate_data, dict) else 0,
        )
        if rate <= 0:
            return {"success": False, "error": "No usable MYST/USD conversion rate was returned."}

        requested_myst = requested_usd / rate
        if requested_myst > balance + 1e-9:
            return {"success": False, "error": f"Requested withdrawal exceeds balance ({balance:.6f} MYST)."}

        payout = await self._request("/identities/" + identity_id + "/payout-address")
        current_address = payout.get("address") if isinstance(payout, dict) else None
        if current_address and str(current_address).lower() != address.lower():
            return {"success": False, "error": "Configured payout address does not match the application wallet."}

        await self._request(
            "/identities/" + identity_id + "/payout-address",
            method="PUT",
            payload={"address": address},
        )
        details = await self._request("/identities/" + identity_id)
        hermes_id = details.get("hermesId") if isinstance(details, dict) else None
        if not hermes_id:
            return {"success": False, "error": "Mysterium identity has no Hermes settlement identifier."}

        await self._request(
            "/transactor/settle/withdraw",
            method="POST",
            payload={
                "hermesId": hermes_id,
                "providerId": identity_id,
                "beneficiary": address,
                "toChainId": 137,
                "amount": f"{requested_myst:.6f}",
            },
        )
        return {
            "success": True,
            "data": {
                "status": "DISPATCHED",
                "providerReference": f"{identity_id}:{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            },
        }


async def _gather_snapshot(provider: MysteriumNodeProvider, identity_id: str) -> tuple[Any, Any, Any, Any, Any]:
    async with httpx.AsyncClient(timeout=provider.timeout) as client:
        headers = provider._headers()

        async def get(path: str) -> Any:
            response = await client.get(provider.base_url + path, headers=headers)
            response.raise_for_status()
            return response.json() if response.text else None

        async def get_optional(path: str, default: Any) -> Any:
            try:
                return await get(path)
            except Exception:
                return default

        health, identity, services, activity, quality = await asyncio.gather(
            get("/healthcheck"),
            get("/identities/" + identity_id),
            get("/services?includeAll=true"),
            get_optional("/node/provider/activity-stats", {"telemetryAvailable": False}),
            get_optional("/node/provider/quality", {"telemetryAvailable": False}),
        )
        return health, identity, services, activity, quality
