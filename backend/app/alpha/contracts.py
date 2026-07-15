from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class AlphaEvent:
    id: str
    tipo: str
    categoria: str
    gravidade: str
    ativo: str | None
    titulo: str
    descricao: str
    impacto: str
    data: str
    status: str
    origem: str


@dataclass(slots=True)
class HealthScore:
    nome: str
    nota: float
    status: str
    justificativa: str


@dataclass(slots=True)
class HealthReport:
    notaGeral: float
    status: str
    scores: list[HealthScore]


@dataclass(slots=True)
class Insight:
    titulo: str
    descricao: str
    prioridade: str
    tipo: str
    impacto: str
    data: str


@dataclass(slots=True)
class ScoreBreakdown:
    nome: str
    nota: float
    justificativa: str


@dataclass(slots=True)
class AlphaScoreV2:
    assetId: str
    ticker: str
    nome: str
    classe: str
    setor: str
    termo: str
    classificacao: str
    scoreFinal: float
    justificativaFinal: str
    scores: list[ScoreBreakdown]


@dataclass(slots=True)
class CopilotQuestion:
    id: str
    pergunta: str
    status: str
    respostaBase: str


def to_dict(value: Any) -> Any:
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value
