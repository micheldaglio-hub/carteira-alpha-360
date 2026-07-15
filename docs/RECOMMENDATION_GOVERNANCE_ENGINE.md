# Recommendation Governance Engine

## Objetivo

O `Recommendation Governance Engine` cria uma trilha institucional para a Carteira Recomendada Alpha. A carteira deixa de ser apenas uma lista de ativos e passa a ter revisao, evidencia, status, risco e gatilhos de reavaliacao.

## O que ele registra

- `reviewId`
- mes do relatorio
- proxima revisao
- score institucional
- confianca Alpha
- confianca dos dados do usuario
- status da recomendacao
- revisao por ativo
- tese
- riscos
- evidencias
- acao de acompanhamento
- gatilhos extraordinarios de revisao

## Persistencia

Quando existe usuario autenticado e banco ativo, o motor grava snapshot em `user_preferences`:

- `recommendation_governance:latest`
- `recommendation_governance:YYYY-MM`

Isso permite historico mensal sem criar dependencia pesada de schema nesta fase.

## Regras de governanca

- Nenhuma carteira e alterada automaticamente.
- Toda troca futura deve gerar novo `reviewId`.
- Dado com fallback reduz conviccao.
- Corte de proventos, aumento de divida, evento regulatorio ou divergencia de fonte exigem revisao extraordinaria.

## Arquivo principal

- `backend/app/services/recommendation_governance_engine.py`

