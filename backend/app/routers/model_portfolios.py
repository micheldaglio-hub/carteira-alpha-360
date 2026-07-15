from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.data_lineage_integrations import record_recommended_portfolio_evidence
from app.services.alpha_b3_screener import run_alpha_b3_screener
from app.services.alpha_crypto_screener import run_alpha_crypto_screener
from app.services.alpha_fii_screener import run_alpha_fii_screener
from app.services.alpha_global_equity_screener import run_alpha_global_equity_screener
from app.services.global_backtest import DEFAULT_GLOBAL_BACKTEST_START, DEFAULT_INITIAL_VALUE_BRL, run_global_backtest
from app.services.model_portfolios import get_model_portfolios


router = APIRouter(prefix="/model-portfolios", tags=["model-portfolios"])


@router.get("")
def list_model_portfolios(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload = get_model_portfolios(db, user_id=user.id)
    report = payload.get("recommendedPortfolioReport") or {}
    payload["dataLineage"] = record_recommended_portfolio_evidence(db, user.id, report)
    return payload


@router.post("/validate")
def validate_model_portfolios(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload = get_model_portfolios(db, user_id=user.id, refresh_market=True)
    report = payload.get("recommendedPortfolioReport") or {}
    payload["dataLineage"] = record_recommended_portfolio_evidence(db, user.id, report)
    return payload


@router.get("/recommended-report")
def get_recommended_portfolio_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = get_model_portfolios(db, user_id=user.id)["recommendedPortfolioReport"]
    report["dataLineage"] = record_recommended_portfolio_evidence(db, user.id, report)
    return report


@router.post("/recommended-report/run")
def run_recommended_portfolio_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = get_model_portfolios(db, user_id=user.id, refresh_market=True)["recommendedPortfolioReport"]
    report["dataLineage"] = record_recommended_portfolio_evidence(db, user.id, report)
    return report


@router.get("/screener")
def get_alpha_b3_screener(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_alpha_b3_screener(db)


@router.post("/screener/run")
def run_alpha_b3_screener_route(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_alpha_b3_screener(db, refresh_market=True)


@router.get("/fii-screener")
def get_alpha_fii_screener(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_alpha_fii_screener(db)


@router.post("/fii-screener/run")
def run_alpha_fii_screener_route(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_alpha_fii_screener(db, refresh_market=True)


@router.get("/global-screener")
def get_alpha_global_screener(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_alpha_global_equity_screener(db)


@router.post("/global-screener/run")
def run_alpha_global_screener_route(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_alpha_global_equity_screener(db, refresh_market=True)


@router.get("/global-backtest")
def get_alpha_global_backtest(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: date = Query(DEFAULT_GLOBAL_BACKTEST_START),
    end_date: date | None = Query(None),
    initial_value: float = Query(DEFAULT_INITIAL_VALUE_BRL, ge=1),
):
    return run_global_backtest(db, start_date=start_date, end_date=end_date, initial_value_brl=initial_value)


@router.post("/global-backtest/run")
def run_alpha_global_backtest_route(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: date = Query(DEFAULT_GLOBAL_BACKTEST_START),
    end_date: date | None = Query(None),
    initial_value: float = Query(DEFAULT_INITIAL_VALUE_BRL, ge=1),
):
    return run_global_backtest(db, start_date=start_date, end_date=end_date, initial_value_brl=initial_value, refresh_market=True)


@router.get("/crypto-screener")
def get_alpha_crypto_screener(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_alpha_crypto_screener(db, user.id)


@router.post("/crypto-screener/run")
def run_alpha_crypto_screener_route(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_alpha_crypto_screener(db, user.id, refresh_market=True)
