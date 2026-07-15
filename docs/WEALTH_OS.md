# Alpha Wealth OS

Status: fundacao implementada em 2026-07-13.

## Objetivo

O Alpha Wealth OS e a camada de comando patrimonial do Carteira Alpha 360. Ele consolida carteira, metas, risco, oportunidades, stress tests, confiabilidade dos dados e Alpha Copilot conversacional.

Ele nao substitui os motores existentes. Ele orquestra:

- Portfolio Engine.
- Alpha Intelligence Engine.
- Financial Projection Engine.
- Asset Engine Universal.
- Market Data Engine.
- Guardian.
- Screener Alpha B3, FIIs, Global e Crypto.
- Macro / FX Engine.
- Tax Engine.
- Strategy Engine 2.0.

## Principio central

Nenhum calculo estrategico deve viver no React. A interface apenas renderiza respostas prontas do backend.

## Arquivos

- `backend/app/wealth_os/service.py`
- `backend/app/wealth_os/contracts.py`
- `backend/app/wealth_os/strategy_engine.py`
- `backend/app/wealth_os/scenario_engine.py`
- `backend/app/wealth_os/copilot_service.py`
- `backend/app/routers/wealth_os.py`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/pages/Strategies.jsx`
- `frontend/src/pages/StressTest.jsx`
- `frontend/src/pages/Copilot.jsx`

## Endpoints

- `GET /api/wealth-os`
- `GET /api/wealth-os/command-center`
- `GET /api/wealth-os/goals`
- `GET /api/wealth-os/score`
- `GET /api/wealth-os/scenarios`
- `GET /api/wealth-os/stress-test`
- `GET /api/wealth-os/opportunities`
- `GET /api/wealth-os/economic`
- `GET /api/wealth-os/macro-fx`
- `GET /api/wealth-os/fx`
- `GET /api/wealth-os/tax`
- `GET /api/wealth-os/strategies`
- `GET /api/wealth-os/data-confidence`
- `GET /api/wealth-os/copilot/questions`
- `GET /api/wealth-os/copilot/answer/{question_id}`
- `GET /api/wealth-os/copilot/status`
- `POST /api/wealth-os/copilot/chat`

## Regra de linguagem

O Wealth OS pode dizer:

- "A carteira pede acompanhamento."
- "Existe concentracao elevada."
- "A exposicao global esta abaixo da meta tecnica."
- "Este ativo deve ser estudado antes de aumentar exposicao."

O Wealth OS nao deve dizer:

- "Compre agora."
- "Venda agora."
- "Este ativo nao tem risco."
- "Rentabilidade garantida."
