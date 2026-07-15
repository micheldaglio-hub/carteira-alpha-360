from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.dependencies import get_current_user
from app.models import User
from app.services.market_data.providers.b3 import B3PublicDataProvider
from app.services.market_data.providers.cvm import CvmPublicDataProvider


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def settings(_: User = Depends(get_current_user)):
    app_settings = get_settings()
    return {
        "appName": app_settings.app_name,
        "environment": app_settings.environment,
        "marketDataProvider": app_settings.market_data_provider,
        "externalSources": [
            {"name": "Mock", "status": "ativo" if app_settings.market_data_provider == "mock" else "disponivel"},
            {
                "name": "BRAPI",
                "status": "ativo" if app_settings.market_data_provider == "brapi" else "preparado",
                "requiresToken": True,
            },
            {
                "name": "CoinMarketCap",
                "status": "ativo" if app_settings.coinmarketcap_api_key else "preparado",
                "requiresToken": True,
                "notes": "Usado para cotacoes de criptomoedas quando COINMARKETCAP_API_KEY esta configurada.",
            },
            *CvmPublicDataProvider().get_available_sources(),
            *B3PublicDataProvider().get_available_sources(),
        ],
        "principles": [
            "Nao promete rentabilidade.",
            "Nao emite recomendacao de compra ou venda.",
            "Mantem dados isolados por usuario.",
            "Permite adicionar IA em camada futura sem alterar o dominio principal.",
        ],
    }
