from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class TransactionCreate(BaseModel):
    ticker: str
    asset_name: str = ""
    asset_class: str = "Acoes"
    sector: str = "Nao classificado"
    segment: str = "Cadastro manual"
    type: str = Field(pattern="^(buy|sell)$")
    date: date
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fees: Decimal = Field(default=0, ge=0)
    broker: str = ""
    notes: str = ""


class DividendCreate(BaseModel):
    ticker: str
    date: date
    amount_per_share: Decimal = Field(default=0, ge=0)
    total_amount: Decimal = Field(gt=0)
    source: str = "manual"


class CryptoTransactionCreate(BaseModel):
    symbol: str
    name: str = ""
    category: str = "outro"
    currency: str = Field(default="BRL", pattern="^(BRL|USD)$")
    type: str = Field(pattern="^(buy|sell)$")
    date: date
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fees: Decimal = Field(default=0, ge=0)
    exchange: str = ""
    wallet: str = ""


class ProjectionRequest(BaseModel):
    initial_wealth: float = Field(default=100000, ge=0)
    monthly_contribution: float = Field(default=2500, ge=0)
    expected_monthly_return: float = Field(default=0.8, ge=-10, le=20)
    expected_annual_dividend_yield: float = Field(default=7.5, ge=0, le=40)
    reinvest_dividends: bool = True
    dividend_reinvestment_rate: float | None = Field(default=None, ge=0, le=100)
    annual_contribution_growth: float = Field(default=0, ge=-100, le=100)
    variable_monthly_returns: list[float] = Field(default_factory=list)
    variable_annual_dividend_yields: list[float] = Field(default_factory=list)
    variable_annual_inflation: list[float] = Field(default_factory=list)
    years: int = Field(default=20, ge=1, le=60)
    annual_inflation: float = Field(default=4.0, ge=0, le=30)
    passive_income_goal: float = Field(default=6000, ge=0)


class DashboardProjectionPremises(BaseModel):
    monthly_contribution: float = Field(default=100, ge=0)
    monthly_return: float = Field(default=1, ge=-10, le=20)


class CopilotChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1200)
    conversation_id: str | None = Field(default=None, max_length=80)


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
