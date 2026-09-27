import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.providers.mysterium import MysteriumNodeProvider


app = FastAPI(title="Autonomous Income Agent Backend", version="0.2.0")


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    providerId: str
    name: str
    description: str
    estimatedHourlyUsd: float = Field(ge=0)
    feeUsd: float = Field(ge=0)
    minimumWithdrawalUsd: float = Field(ge=0)
    requiresCapital: bool
    requiresKyc: bool
    automationAllowed: bool
    supportedCountries: list[str] = Field(default_factory=list)
    riskLevel: str
    eligibilityStatus: str
    sourceUrl: HttpUrl
    lastVerifiedAt: datetime
    score: float = 0.0


class WithdrawalRequest(BaseModel):
    amountUsd: float = Field(gt=0)
    wallet: dict[str, Any]


USER_COUNTRY = os.getenv("AGENT_COUNTRY", "Iran").strip()
WITHDRAWALS_ENABLED = os.getenv("AGENT_WITHDRAWALS_ENABLED", "false").strip().lower() == "true"
INTERVAL_MINUTES = max(1, int(os.getenv("AGENT_SCAN_INTERVAL_MINUTES", "360")))

mysterium_provider = MysteriumNodeProvider()
opportunity_cache: list[dict[str, Any]] = []
state: dict[str, Any] = {
    "status": "IDLE",
    "providerCount": 1,
    "opportunityCount": 0,
    "lastScanAt": None,
    "lastRunResult": None,
    "country": USER_COUNTRY,
    "withdrawalsEnabled": WITHDRAWALS_ENABLED,
}


async def scan() -> dict[str, Any]:
    global opportunity_cache
    state["status"] = "RUNNING"
    try:
        discovered = await mysterium_provider.discover(USER_COUNTRY)
        opportunity_cache = discovered
        state["opportunityCount"] = len(discovered)
        state["lastScanAt"] = datetime.now(timezone.utc).isoformat()
        state["lastRunResult"] = {
            "success": True,
            "message": (
                "Discovery completed across the configured production provider; "
                f"{len(discovered)} eligible opportunity record(s) found."
            ),
            "timestamp": state["lastScanAt"],
        }
        state["status"] = "IDLE"
        return {
            "ok": True,
            "providerCount": 1,
            "opportunityCount": len(discovered),
            "message": state["lastRunResult"]["message"],
        }
    except Exception as exc:
        state["status"] = "ERROR"
        state["lastRunResult"] = {
            "success": False,
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return {"ok": False, "error": str(exc)}
    finally:
        if state["status"] == "RUNNING":
            state["status"] = "IDLE"


@app.get("/health")
async def health() -> dict[str, Any]:
    status = await mysterium_provider.get_runtime_status()
    return {
        "status": "ok",
        "headlessAgent": True,
        "country": USER_COUNTRY,
        "productionProviders": [
            {
                "id": "mysterium-node",
                "name": "Mysterium Node",
                "executionMode": "PERSISTENT",
                "productionReady": True,
                "officialApiAvailable": True,
                "requiresCapital": False,
                "automationAllowed": True,
                "supportedCurrencies": ["MYST"],
                "supportedNetworks": ["POLYGON"],
            }
        ],
        "mysterium": status,
        "state": state,
    }


@app.get("/agent/status")
async def agent_status() -> dict[str, Any]:
    return {
        **state,
        "scheduler": {
            "intervalMinutes": INTERVAL_MINUTES,
        },
    }


@app.post("/agent/run")
async def agent_run() -> dict[str, Any]:
    return await scan()


@app.get("/opportunities", response_model=list[Opportunity])
async def opportunities() -> list[dict[str, Any]]:
    return opportunity_cache


@app.get("/providers/mysterium-node/status")
async def mysterium_status() -> dict[str, Any]:
    return await mysterium_provider.get_runtime_status()


@app.post("/providers/mysterium-node/execute")
async def mysterium_execute(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": False,
        "error": (
            "Mysterium is a persistent provider. Income accrues while the node "
            "services run; there is no per-opportunity execution action."
        ),
    }


@app.post("/providers/mysterium-node/verify-payment")
async def mysterium_verify_payment(payload: dict[str, Any]) -> dict[str, Any]:
    return await mysterium_provider.verify_payment(
        str(payload.get("paymentId", "")),
        payload.get("opportunity"),
    )


@app.post("/providers/mysterium-node/withdraw")
async def mysterium_withdraw(payload: WithdrawalRequest) -> dict[str, Any]:
    if not WITHDRAWALS_ENABLED:
        return {
            "success": False,
            "error": (
                "Real withdrawals are disabled. Set AGENT_WITHDRAWALS_ENABLED=true "
                "only after the payout address and provider state have been verified."
            ),
        }
    return await mysterium_provider.request_withdrawal(
        payload.amountUsd,
        payload.wallet,
    )


@app.on_event("startup")
async def startup_scan() -> None:
    if os.getenv("AGENT_SCAN_ON_STARTUP", "true").lower() == "true":
        await scan()


async def scheduled_loop() -> None:
    while True:
        await asyncio.sleep(INTERVAL_MINUTES * 60)
        await scan()


if os.getenv("AGENT_ENABLE_SCHEDULER", "false").lower() == "true":
    @app.on_event("startup")
    async def startup_scheduler() -> None:
        asyncio.create_task(scheduled_loop())
