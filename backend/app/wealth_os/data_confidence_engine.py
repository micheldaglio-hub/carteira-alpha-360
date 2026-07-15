from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.portfolio import get_positions
from app.wealth_os.contracts import DataConfidenceItem


def build_data_confidence(db: Session, user_id: str) -> list[DataConfidenceItem]:
    positions = get_positions(db, user_id)
    total_assets = len(positions)
    priced_assets = sum(1 for item in positions if float(item.get("currentPrice") or 0) > 0)
    proceeds_assets = sum(1 for item in positions if float(item.get("dividendsReceived") or 0) > 0)
    classified_assets = sum(1 for item in positions if item.get("sector") and item.get("sector") != "Nao classificado")

    price_confidence = round(priced_assets / total_assets * 100, 2) if total_assets else 0
    classification_confidence = round(classified_assets / total_assets * 100, 2) if total_assets else 0
    proceeds_confidence = round(proceeds_assets / total_assets * 100, 2) if total_assets else 0

    return [
        DataConfidenceItem(
            area="Posicoes da carteira",
            status="confirmado" if total_assets else "vazio",
            confidenceScore=100 if total_assets else 0,
            source="movimentacoes_internas",
            reading="As quantidades e precos medios saem das compras e vendas cadastradas pelo usuario.",
            nextStep="Manter compras, vendas, proventos e taxas sempre registrados.",
        ),
        DataConfidenceItem(
            area="Precos atuais",
            status="parcial" if price_confidence < 100 and total_assets else "confirmado",
            confidenceScore=price_confidence,
            source="Market Data Engine + fallback interno",
            reading=f"{priced_assets}/{total_assets} ativos possuem preco atual calculavel.",
            nextStep="Sincronizar dados de mercado e revisar ativos com preco zerado.",
        ),
        DataConfidenceItem(
            area="Setores e classes",
            status="parcial" if classification_confidence < 100 and total_assets else "confirmado",
            confidenceScore=classification_confidence,
            source="Asset Engine Universal",
            reading=f"{classified_assets}/{total_assets} ativos possuem setor classificado.",
            nextStep="Completar classificacoes para melhorar concentracao, Guardian e rebalanceamento.",
        ),
        DataConfidenceItem(
            area="Proventos",
            status="estimado" if proceeds_confidence < 60 else "parcial",
            confidenceScore=proceeds_confidence,
            source="registros internos + providers de mercado",
            reading=f"{proceeds_assets}/{total_assets} ativos tem historico interno de proventos.",
            nextStep="Registrar dividendos, JCP e rendimentos de FIIs para aumentar a leitura de renda passiva.",
        ),
        DataConfidenceItem(
            area="Cenario macro e fiscal",
            status="parcial",
            confidenceScore=65,
            source="Macro / FX Engine + Tax Engine",
            reading="Selic, IPCA e cambio ja usam Banco Central SGS. Impostos possuem estimativa operacional para acoes, FIIs e JCP.",
            nextStep="Adicionar compensacao de prejuizos, day trade, imposto internacional e trilha de DARF paga.",
        ),
    ]
