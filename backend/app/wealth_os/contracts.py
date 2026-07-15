from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class WealthGoal:
    id: str
    title: str
    description: str
    currentValue: float
    targetValue: float
    progressPct: float
    remainingValue: float
    estimatedMonths: int | None
    requiredMonthlyContribution: float | None
    status: str
    confidence: str
    assumptions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WealthProgressFactor:
    name: str
    score: float
    status: str
    reading: str
    impact: str


@dataclass(slots=True)
class WealthProgressScore:
    score: float
    status: str
    headline: str
    factors: list[WealthProgressFactor]
    strengths: list[str]
    attentionPoints: list[str]
    nextActions: list[str]


@dataclass(slots=True)
class DataConfidenceItem:
    area: str
    status: str
    confidenceScore: float
    source: str
    reading: str
    nextStep: str


@dataclass(slots=True)
class ScenarioResult:
    id: str
    title: str
    description: str
    impactValue: float
    impactPct: float
    severity: str
    reading: str
    category: str = "portfolio"
    shockedEquity: float = 0
    stressedEquity: float = 0
    passiveIncomeBefore: float = 0
    passiveIncomeAfter: float = 0
    passiveIncomeImpact: float = 0
    bucketImpacts: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    recommendedActions: list[str] = field(default_factory=list)
    dataUsed: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StressTestReport:
    status: str
    headline: str
    baseEquity: float
    basePassiveIncome: float
    worstScenarioId: str
    worstImpactValue: float
    worstImpactPct: float
    resilienceScore: float
    riskLevel: str
    exposureBreakdown: dict[str, float]
    scenarios: list[ScenarioResult]
    macroContext: list[str]
    assumptions: list[str]
    updatedAt: str


@dataclass(slots=True)
class OpportunityStudy:
    id: str
    title: str
    asset: str | None
    category: str
    priority: str
    thesis: str
    evidence: list[str]
    risks: list[str]
    nextStep: str
    confidence: str


@dataclass(slots=True)
class EconomicReading:
    id: str
    title: str
    status: str
    reading: str
    portfolioImpact: str
    dataSources: list[str]
    confidence: str


@dataclass(slots=True)
class MacroIndicator:
    id: str
    title: str
    value: float
    unit: str
    period: str
    trend: str
    status: str
    source: str
    sourceCode: str
    asOf: str
    qualityScore: float
    reading: str
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FxRateSnapshot:
    pair: str
    baseCurrency: str
    quoteCurrency: str
    rate: float
    source: str
    sourceCode: str
    asOf: str
    status: str
    qualityScore: float
    reading: str
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MacroPortfolioReading:
    id: str
    title: str
    severity: str
    reading: str
    portfolioImpact: str
    dataUsed: list[str]


@dataclass(slots=True)
class MacroFxSnapshot:
    status: str
    headline: str
    updatedAt: str
    indicators: list[MacroIndicator]
    fxRates: list[FxRateSnapshot]
    portfolioReadings: list[MacroPortfolioReading]
    sourceHealth: list[DataConfidenceItem]
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TaxRule:
    id: str
    jurisdiction: str
    title: str
    summary: str
    rate: float | None
    source: str
    status: str


@dataclass(slots=True)
class TaxEstimateItem:
    id: str
    category: str
    assetClass: str
    jurisdiction: str
    grossAmount: float
    taxableAmount: float
    estimatedTax: float
    netAmount: float
    rate: float
    status: str
    reading: str
    dataUsed: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TaxReport:
    status: str
    headline: str
    period: str
    jurisdiction: str
    grossIncome: float
    realizedGain: float
    estimatedWithheldTax: float
    estimatedTaxDue: float
    netIncomeAfterEstimatedTax: float
    items: list[TaxEstimateItem]
    rules: list[TaxRule]
    alerts: list[str]
    dataGaps: list[str]
    updatedAt: str


@dataclass(slots=True)
class StrategyDefinition:
    id: str
    name: str
    archetype: str
    description: str
    riskProfile: str
    timeHorizon: str
    philosophy: list[str]
    targetAllocation: dict[str, float]


@dataclass(slots=True)
class StrategyFactorResult:
    id: str
    label: str
    score: float
    status: str
    reading: str
    weight: float


@dataclass(slots=True)
class StrategyAssetFit:
    ticker: str
    name: str
    assetClass: str
    sector: str
    score: float
    fit: str
    reading: str


@dataclass(slots=True)
class StrategyAssessment:
    strategy: StrategyDefinition
    score: float
    classification: str
    headline: str
    factors: list[StrategyFactorResult]
    currentAllocation: dict[str, float]
    allocationGaps: dict[str, float]
    strengths: list[str]
    attentionPoints: list[str]
    nextStudies: list[str]
    assetFits: list[StrategyAssetFit]


@dataclass(slots=True)
class StrategyEngineReport:
    status: str
    headline: str
    primaryStrategy: str
    primaryScore: float
    currentAllocation: dict[str, float]
    metrics: dict[str, float]
    assessments: list[StrategyAssessment]
    rules: list[str]
    updatedAt: str


@dataclass(slots=True)
class CopilotQuestion:
    id: str
    question: str
    category: str
    answer: str
    dataUsed: list[str]
    confidence: str


@dataclass(slots=True)
class CopilotCitation:
    id: str
    title: str
    source: str
    dataPath: str
    confidence: str
    excerpt: str
    value: str = ""


@dataclass(slots=True)
class CopilotChatResponse:
    id: str
    question: str
    answer: str
    confidence: str
    mode: str
    provider: str
    citations: list[CopilotCitation]
    followUps: list[str]
    warnings: list[str]
    dataUsed: list[str]


@dataclass(slots=True)
class WealthEventV2:
    id: str
    eventType: str
    category: str
    severity: str
    priority: str
    asset: str | None
    title: str
    message: str
    impact: str
    recommendedAction: str
    status: str
    source: str
    triggeredAt: str
    lifecycleStage: str
    confidence: str
    readOnly: bool = True
    dataUsed: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GuardianItem:
    id: str
    type: str
    category: str
    severity: str
    priority: str
    title: str
    message: str
    impact: str
    recommendedAction: str
    asset: str | None
    status: str
    source: str
    triggeredAt: str
    confidence: str
    dataUsed: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GuardianReport:
    status: str
    headline: str
    summary: dict[str, int]
    items: list[GuardianItem]


@dataclass(slots=True)
class ResearchEvidence:
    id: str
    type: str
    source: str
    title: str
    reading: str
    confidenceScore: float
    asOf: str
    url: str = ""


@dataclass(slots=True)
class ResearchNewsItem:
    id: str
    ticker: str
    title: str
    summary: str
    source: str
    publishedAt: str
    url: str
    sentiment: str
    relevanceScore: float


@dataclass(slots=True)
class AssetResearchReport:
    ticker: str
    name: str
    assetClass: str
    sector: str
    researchScore: float
    status: str
    headline: str
    thesis: str
    evidence: list[ResearchEvidence]
    news: list[ResearchNewsItem]
    risks: list[str]
    opportunities: list[str]
    dataGaps: list[str]
    confidence: str
    updatedAt: str


@dataclass(slots=True)
class ResearchCenterReport:
    status: str
    headline: str
    coverage: dict[str, int]
    sourceHealth: list[DataConfidenceItem]
    reports: list[AssetResearchReport]
    newsFeed: list[ResearchNewsItem]


@dataclass(slots=True)
class WealthCommandCenter:
    greeting: str
    headline: str
    mission: str
    totalWealth: float
    investedValue: float
    pnlPct: float
    passiveIncome: float
    eventsCount: int
    wealthProgressScore: WealthProgressScore
    topGoals: list[WealthGoal]
    opportunities: list[OpportunityStudy]
    scenarios: list[ScenarioResult]
    dataConfidence: list[DataConfidenceItem]
    copilotQuestions: list[CopilotQuestion]


def to_dict(value: Any) -> Any:
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))
