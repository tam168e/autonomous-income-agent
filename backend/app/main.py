from datetime import datetime, timezone
from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl, Field

app = FastAPI(title="Autonomous Income Agent Backend", version="0.1.0")

class Opportunity(BaseModel):
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
    riskLevel: str
    eligibilityStatus: str
    sourceUrl: HttpUrl
    lastVerifiedAt: datetime

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc)}

@app.get("/opportunities", response_model=list[Opportunity])
def opportunities():
    # Intentionally empty: no fake opportunities or fake earnings.
    # Add verified provider adapters on the backend.
    return []
