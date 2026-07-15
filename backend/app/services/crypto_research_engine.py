from __future__ import annotations

import re
from math import isfinite
from typing import Any

import httpx

from app.core.config import get_settings


RESEARCH_PROFILES: dict[str, dict[str, Any]] = {
    "FET": {
        "name": "Fetch.ai",
        "themes": ["IA", "agentes autonomos", "infraestrutura"],
        "narrativeScore": 92,
        "moatScore": 74,
        "catalysts": [
            "Narrativa de inteligencia artificial continua sendo uma das teses mais fortes do ciclo cripto.",
            "Exposicao a agentes autonomos e infraestrutura de IA, tema que pode atrair fluxo especulativo.",
            "Alta disponibilidade em exchanges grandes melhora entrada, saida e acompanhamento.",
        ],
        "risks": [
            "A narrativa de IA pode ficar saturada e sofrer correcao forte apos movimentos rapidos.",
            "Precisa provar uso real e captura de valor para o token, nao apenas narrativa.",
            "Concorrencia grande em IA cripto e risco de reprecificacao contra projetos mais novos.",
        ],
        "thesis": "FET entra como tese de IA cripto: busca capturar fluxo especulativo em agentes autonomos e infraestrutura de inteligencia artificial.",
    },
    "JASMY": {
        "name": "JasmyCoin",
        "themes": ["IoT", "soberania de dados", "Japao"],
        "narrativeScore": 82,
        "moatScore": 64,
        "catalysts": [
            "Preco unitario baixo e disponibilidade na Binance facilitam exposicao simbolica.",
            "Narrativa de soberania de dados e IoT pode ganhar tracao se houver entregas corporativas reais.",
            "Projeto tem apelo de assimetria para capital pequeno, desde que liquidez continue saudavel.",
        ],
        "risks": [
            "Supply elevado limita comparacoes simples com XRP, ADA ou outros ativos de menor oferta.",
            "A tese depende de execucao real em IoT/dados, nao apenas preco baixo.",
            "Pode lateralizar por longos periodos se a narrativa de IoT nao ganhar fluxo.",
        ],
        "thesis": "JASMY entra como tese de baixo valor unitario, IoT e soberania de dados, com operacional simples via Binance.",
    },
    "GALA": {
        "name": "Gala",
        "themes": ["games", "entretenimento", "metaverso"],
        "narrativeScore": 68,
        "moatScore": 52,
        "catalysts": [
            "Games podem voltar a performar em ciclos de maior apetite a risco.",
            "Preco baixo e liquidez podem atrair fluxo especulativo.",
        ],
        "risks": [
            "Narrativa de games ja decepcionou em ciclos anteriores.",
            "Dependencia de usuarios reais e economia de jogos sustentavel.",
            "Risco alto de hype sem captura de valor para o token.",
        ],
        "thesis": "GALA e uma tese de games/entretenimento com alto beta, mas exige maior desconto de risco.",
    },
    "VET": {
        "name": "VeChain",
        "themes": ["supply chain", "enterprise", "rastreabilidade"],
        "narrativeScore": 72,
        "moatScore": 63,
        "catalysts": [
            "Tese enterprise e supply chain possui utilidade mais compreensivel que muitos tokens puramente narrativos.",
            "Pode se beneficiar se projetos corporativos voltarem a ganhar fluxo no mercado cripto.",
        ],
        "risks": [
            "Tese antiga pode ter menor novidade para capturar fluxo especulativo.",
            "Adocao enterprise pode ser lenta e nao se traduzir diretamente em preco.",
        ],
        "thesis": "VET e uma tese de rastreabilidade e uso empresarial, mais madura, mas talvez com menor explosividade narrativa.",
    },
    "GRT": {
        "name": "The Graph",
        "themes": ["dados", "indexacao", "infraestrutura"],
        "narrativeScore": 76,
        "moatScore": 70,
        "catalysts": [
            "Indexacao e dados sao infraestrutura essencial para aplicacoes blockchain.",
            "Narrativa de dados pode se conectar a IA, analytics e web3.",
        ],
        "risks": [
            "Projeto mais conhecido pode ter assimetria menor que small caps.",
            "Precisa manter demanda real por servicos de indexacao e captura de valor pelo token.",
        ],
        "thesis": "GRT e uma tese de infraestrutura de dados, menos meme e mais utilidade, com assimetria moderada.",
    },
    "ADA": {
        "name": "Cardano",
        "themes": ["smart contracts", "ecossistema"],
        "narrativeScore": 62,
        "moatScore": 66,
        "catalysts": [
            "Alta liquidez e comunidade ampla reduzem risco operacional.",
            "Pode se recuperar em ciclos de alta de large caps alternativas.",
        ],
        "risks": [
            "Market cap elevado reduz o perfil de multiplicacao extrema.",
            "Ecossistema precisa mostrar tracao frente a concorrentes mais ativos.",
        ],
        "thesis": "ADA e mais uma tese de large cap alternativa do que uma assimetria agressiva de cripto do mes.",
    },
}


class CryptoResearchEngine:
    """Deep research layer for monthly crypto opportunities.

    The screener finds candidates. This engine validates whether the candidate deserves to become the monthly study.
    It does not promise returns and does not issue direct buy/sell orders.
    """

    def __init__(self, timeout: float = 10.0) -> None:
        self.settings = get_settings()
        self.timeout = timeout

    def research_candidates(self, candidates: list[dict], holdings: dict[str, dict] | None = None) -> dict:
        holdings = holdings or {}
        reports = [self.research_candidate(candidate, holdings) for candidate in candidates[:8]]
        reports = sorted(reports, key=lambda item: item["researchScore"], reverse=True)
        selected = reports[0] if reports else None
        return {
            "engine": "Crypto Research Engine",
            "methodology": [
                "Screener encontra oportunidades liquidas na Binance.",
                "Research valida narrativa, tokenomics, supply, liquidez, momento, risco e catalisadores.",
                "O destaque mensal depende do research score, nao apenas de preco baixo.",
                "A decisao final separa nova oportunidade de reforco de tese ja existente.",
            ],
            "selected": selected,
            "reports": reports,
        }

    def research_candidate(self, candidate: dict, holdings: dict[str, dict] | None = None) -> dict:
        holdings = holdings or {}
        ticker = str(candidate.get("ticker") or "").upper()
        profile = RESEARCH_PROFILES.get(ticker, {})
        external = {}
        if candidate.get("source") != "fallback":
            external = self._fetch_external_detail(ticker, str(candidate.get("name") or ticker))
        merged = {**candidate}
        for key, value in external.items():
            if value not in (None, "", [], {}):
                merged[key] = value

        price = _float(merged.get("priceUsd"))
        market_cap = _float(merged.get("marketCapUsd"))
        volume = _float(merged.get("volumeUsd"))
        fdv = _float(merged.get("fullyDilutedValuationUsd"))
        circulating_supply = _float(merged.get("circulatingSupply"))
        total_supply = _float(merged.get("totalSupply"))
        max_supply = _float(merged.get("maxSupply"))
        change_30d = _float(merged.get("priceChange30dPct"))
        change_7d = _float(merged.get("priceChange7dPct"))

        scores = {
            "screener": min(_float(candidate.get("alphaScore")), 100),
            "narrativa": _narrative_score(profile, external),
            "tokenomics": _tokenomics_score(circulating_supply, total_supply, max_supply, fdv, market_cap),
            "liquidez": _liquidity_score(volume, market_cap),
            "assimetria": _asymmetry_score(price, market_cap),
            "momento": _momentum_score(change_7d, change_30d),
            "risco": _risk_quality_score(profile, fdv, market_cap, change_7d, change_30d),
            "carteira": _portfolio_fit_score(ticker, holdings),
        }
        research_score = round(
            scores["screener"] * 0.18
            + scores["narrativa"] * 0.18
            + scores["tokenomics"] * 0.14
            + scores["liquidez"] * 0.12
            + scores["assimetria"] * 0.16
            + scores["momento"] * 0.08
            + scores["risco"] * 0.10
            + scores["carteira"] * 0.04,
            2,
        )

        red_flags = _red_flags(merged, profile)
        catalysts = list(profile.get("catalysts") or []) or _default_catalysts(ticker)
        risks = list(profile.get("risks") or []) + red_flags
        already_holds = ticker in holdings
        decision_type = "reforcar_tese_existente" if already_holds else "nova_oportunidade"
        status = _research_status(research_score, red_flags)

        return {
            "ticker": ticker,
            "name": str(merged.get("name") or profile.get("name") or ticker),
            "researchScore": research_score,
            "researchStatus": status,
            "decisionType": decision_type,
            "decisionLabel": "Reforcar tese existente" if already_holds else "Nova oportunidade do mes",
            "conviction": _conviction_label(research_score),
            "scoreBreakdown": scores,
            "thesis": _research_thesis(ticker, profile, merged, research_score),
            "catalysts": catalysts[:5],
            "riskFactors": risks[:7],
            "dueDiligence": _due_diligence_checks(merged, scores, red_flags),
            "scenarios": _scenarios(merged),
            "tokenomics": {
                "priceUsd": round(price, 8),
                "marketCapUsd": round(market_cap, 2),
                "fullyDilutedValuationUsd": round(fdv, 2),
                "volumeUsd": round(volume, 2),
                "circulatingSupply": round(circulating_supply, 2),
                "totalSupply": round(total_supply, 2),
                "maxSupply": round(max_supply, 2),
                "fdvToMarketCap": round(fdv / market_cap, 2) if market_cap and fdv else None,
                "volumeToMarketCapPct": round(volume / market_cap * 100, 2) if market_cap and volume else None,
            },
            "market": {
                "priceChange24hPct": round(_float(merged.get("priceChange24hPct")), 2),
                "priceChange7dPct": round(change_7d, 2),
                "priceChange30dPct": round(change_30d, 2),
                "binancePairs": merged.get("binancePairs") or [],
                "source": merged.get("source") or external.get("source") or "research",
                "categories": external.get("categories") or profile.get("themes") or [],
            },
            "finalVerdict": _final_verdict(ticker, research_score, status, decision_type),
            "disclaimer": "Estudo especulativo de alto risco. Nao promete valorizacao e nao representa ordem automatica de compra.",
        }

    def _fetch_external_detail(self, ticker: str, name: str) -> dict:
        try:
            coin_id = self._coingecko_coin_id(ticker, name)
            if not coin_id:
                return {}
            headers = {"Accept": "application/json"}
            if self.settings.coingecko_api_key:
                headers["x-cg-demo-api-key"] = self.settings.coingecko_api_key
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.settings.coingecko_base_url.rstrip('/')}/coins/{coin_id}",
                    headers=headers,
                    params={
                        "localization": "false",
                        "tickers": "false",
                        "market_data": "true",
                        "community_data": "true",
                        "developer_data": "true",
                        "sparkline": "false",
                    },
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return {}
        market = data.get("market_data") or {}
        description = (data.get("description") or {}).get("en") or ""
        return {
            "name": data.get("name"),
            "source": "coingecko_detail",
            "categories": data.get("categories") or [],
            "description": _clean_description(description),
            "priceUsd": ((market.get("current_price") or {}).get("usd")),
            "marketCapUsd": ((market.get("market_cap") or {}).get("usd")),
            "fullyDilutedValuationUsd": ((market.get("fully_diluted_valuation") or {}).get("usd")),
            "volumeUsd": ((market.get("total_volume") or {}).get("usd")),
            "priceChange24hPct": market.get("price_change_percentage_24h"),
            "priceChange7dPct": market.get("price_change_percentage_7d"),
            "priceChange30dPct": market.get("price_change_percentage_30d"),
            "circulatingSupply": market.get("circulating_supply"),
            "totalSupply": market.get("total_supply"),
            "maxSupply": market.get("max_supply"),
        }

    def _coingecko_coin_id(self, ticker: str, name: str) -> str:
        try:
            headers = {"Accept": "application/json"}
            if self.settings.coingecko_api_key:
                headers["x-cg-demo-api-key"] = self.settings.coingecko_api_key
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.settings.coingecko_base_url.rstrip('/')}/search",
                    headers=headers,
                    params={"query": ticker},
                )
                response.raise_for_status()
                rows = response.json().get("coins") or []
        except Exception:
            return ""
        exact = [
            row for row in rows
            if str(row.get("symbol") or "").upper() == ticker and row.get("id")
        ]
        if exact:
            named = [
                row for row in exact
                if name and name.lower().split()[0] in str(row.get("name") or "").lower()
            ]
            return str((named[0] if named else exact[0]).get("id") or "")
        return str((rows[0] if rows else {}).get("id") or "")


def _narrative_score(profile: dict, external: dict) -> float:
    base = float(profile.get("narrativeScore", 54))
    categories = " ".join(str(item).lower() for item in external.get("categories") or [])
    bonus_terms = ["artificial intelligence", "ai", "depin", "iot", "data", "infrastructure", "privacy"]
    bonus = sum(2 for term in bonus_terms if term in categories)
    return min(100, base + bonus)


def _tokenomics_score(circulating: float, total: float, max_supply: float, fdv: float, market_cap: float) -> float:
    score = 64.0
    reference_supply = max_supply or total
    if reference_supply and circulating:
        unlocked = circulating / reference_supply
        if unlocked >= 0.85:
            score += 14
        elif unlocked >= 0.55:
            score += 7
        elif unlocked < 0.25:
            score -= 16
    if fdv and market_cap:
        ratio = fdv / market_cap
        if ratio <= 1.4:
            score += 12
        elif ratio <= 2.5:
            score += 4
        elif ratio > 5:
            score -= 20
    return max(0, min(100, score))


def _liquidity_score(volume: float, market_cap: float) -> float:
    if volume <= 0:
        return 20
    score = 45.0
    if volume >= 25_000_000:
        score += 25
    elif volume >= 5_000_000:
        score += 18
    elif volume >= 1_000_000:
        score += 10
    if market_cap and volume / market_cap >= 0.05:
        score += 14
    elif market_cap and volume / market_cap >= 0.015:
        score += 7
    return max(0, min(100, score))


def _asymmetry_score(price: float, market_cap: float) -> float:
    score = 50.0
    if 0 < price <= 0.01:
        score += 18
    elif price <= 0.05:
        score += 14
    elif price <= 0.2:
        score += 10
    elif price <= 1:
        score += 5
    if 50_000_000 <= market_cap <= 700_000_000:
        score += 22
    elif 700_000_000 < market_cap <= 2_000_000_000:
        score += 14
    elif 2_000_000_000 < market_cap <= 8_000_000_000:
        score += 6
    elif market_cap > 15_000_000_000:
        score -= 16
    return max(0, min(100, score))


def _momentum_score(change_7d: float, change_30d: float) -> float:
    score = 60.0
    if -20 <= change_30d <= 45:
        score += 12
    elif change_30d > 90:
        score -= 18
    if -12 <= change_7d <= 30:
        score += 8
    elif change_7d > 55:
        score -= 12
    return max(0, min(100, score))


def _risk_quality_score(profile: dict, fdv: float, market_cap: float, change_7d: float, change_30d: float) -> float:
    score = float(profile.get("moatScore", 52))
    if fdv and market_cap and fdv / market_cap > 5:
        score -= 20
    if change_7d > 60 or change_30d > 140:
        score -= 16
    return max(0, min(100, score))


def _portfolio_fit_score(ticker: str, holdings: dict[str, dict]) -> float:
    holding = holdings.get(ticker)
    if not holding:
        return 62
    value = _float(holding.get("currentValue"))
    return_pct = _float(holding.get("returnPct"))
    score = 68.0
    if value < 100:
        score += 12
    if return_pct < -10:
        score += 8
    if value > 1000:
        score -= 10
    return max(0, min(100, score))


def _red_flags(data: dict, profile: dict) -> list[str]:
    flags = []
    market_cap = _float(data.get("marketCapUsd"))
    volume = _float(data.get("volumeUsd"))
    fdv = _float(data.get("fullyDilutedValuationUsd"))
    change_7d = _float(data.get("priceChange7dPct"))
    change_30d = _float(data.get("priceChange30dPct"))
    if market_cap and volume and volume / market_cap < 0.005:
        flags.append("Volume baixo em relacao ao market cap; entrada e saida podem ficar piores em estresse.")
    if fdv and market_cap and fdv / market_cap > 5:
        flags.append("FDV muito acima do market cap, sugerindo risco de desbloqueios/diluicao.")
    if change_7d > 60 or change_30d > 140:
        flags.append("Movimento recente muito esticado; risco de comprar depois de pump curto.")
    if not profile:
        flags.append("Narrativa ainda nao possui perfil proprietario completo no Alpha.")
    return flags


def _due_diligence_checks(data: dict, scores: dict[str, float], red_flags: list[str]) -> list[dict]:
    return [
        {"label": "Acesso em exchange grande", "status": "ok" if data.get("binancePairs") else "atencao"},
        {"label": "Liquidez", "status": "ok" if scores["liquidez"] >= 60 else "atencao"},
        {"label": "Tokenomics e supply", "status": "ok" if scores["tokenomics"] >= 60 else "atencao"},
        {"label": "Narrativa/catalisadores", "status": "ok" if scores["narrativa"] >= 70 else "atencao"},
        {"label": "Red flags criticas", "status": "atencao" if red_flags else "ok"},
    ]


def _scenarios(data: dict) -> list[dict]:
    price = _float(data.get("priceUsd"))
    market_cap = _float(data.get("marketCapUsd"))
    return [
        {
            "name": "Cenario defensivo",
            "description": "Narrativa perde forca ou mercado corrige; queda relevante ou longa lateralizacao continua possivel.",
            "studyMultiple": "0,3x a 1,0x do capital exposto",
            "marketCapReference": round(market_cap * 0.5, 2) if market_cap else None,
        },
        {
            "name": "Cenario base",
            "description": "Narrativa segue viva, liquidez continua saudavel e o ativo acompanha recuperacao do setor.",
            "studyMultiple": "1,5x a 3,0x como estudo hipotetico",
            "marketCapReference": round(market_cap * 2, 2) if market_cap else None,
        },
        {
            "name": "Cenario agressivo",
            "description": "Fluxo forte entra na narrativa e o projeto entrega catalisadores; ainda assim nao e promessa.",
            "studyMultiple": "3,0x a 8,0x como teto especulativo de estudo",
            "marketCapReference": round(market_cap * 5, 2) if market_cap else None,
        },
    ]


def _default_catalysts(ticker: str) -> list[str]:
    return [
        f"{ticker} passou nos filtros de acesso, liquidez e assimetria do screener.",
        "Pode capturar fluxo se sua narrativa ganhar tracao no ciclo atual.",
    ]


def _research_status(score: float, red_flags: list[str]) -> str:
    if score >= 78 and len(red_flags) <= 1:
        return "aprovada_para_estudo_do_mes"
    if score >= 68:
        return "observacao_forte"
    if score >= 55:
        return "watchlist"
    return "reprovada_no_research"


def _conviction_label(score: float) -> str:
    if score >= 82:
        return "Alta conviccao especulativa"
    if score >= 72:
        return "Boa assimetria"
    if score >= 62:
        return "Monitorar"
    return "Fora dos criterios atuais"


def _research_thesis(ticker: str, profile: dict, data: dict, score: float) -> str:
    base = profile.get("thesis") or f"{ticker} foi selecionada pelo screener e precisa de acompanhamento adicional."
    market_cap = _float(data.get("marketCapUsd"))
    volume = _float(data.get("volumeUsd"))
    return (
        f"{base} Research Score {score}/100. "
        f"A leitura combina market cap de estudo em USD {market_cap:,.0f}, volume 24h em USD {volume:,.0f}, "
        "acesso em Binance e avaliacao de risco/tokenomics. A tese so permanece valida se liquidez, narrativa e execucao continuarem vivas."
    )


def _final_verdict(ticker: str, score: float, status: str, decision_type: str) -> str:
    action = "reforco controlado de tese existente" if decision_type == "reforcar_tese_existente" else "nova oportunidade especulativa"
    if status == "aprovada_para_estudo_do_mes":
        return f"{ticker} fica elegivel como {action} no estudo do mes, com risco extremo e exposicao simbolica."
    if status == "observacao_forte":
        return f"{ticker} tem boa leitura, mas exige confirmacao de riscos antes de virar tese principal."
    return f"{ticker} nao possui conviccao suficiente para ser tratada como destaque principal sem novas evidencias."


def _clean_description(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) <= 420:
        return clean
    return clean[:420].rsplit(" ", 1)[0] + "..."


def _float(value) -> float:
    try:
        number = float(value or 0)
        return number if isfinite(number) else 0.0
    except Exception:
        return 0.0
