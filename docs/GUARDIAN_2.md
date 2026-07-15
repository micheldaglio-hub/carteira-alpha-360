# Guardian 2.0

Status: fundacao implementada em 2026-07-13.

## Objetivo

O Guardian 2.0 e o motor de monitoramento preventivo do Carteira Alpha 360.

Ele observa:

- Saude geral da carteira.
- Fatores fracos de saude.
- Concentracao individual.
- Concentracao setorial.
- Ativos em revisao pelo Alpha Score.
- Distancia da meta de renda passiva.
- Confianca dos dados.
- Wealth Progress Score.

## Arquivo

- `backend/app/wealth_os/guardian_engine.py`

## Saida

Cada item possui:

- Categoria.
- Severidade.
- Prioridade.
- Mensagem humana.
- Impacto.
- Acao sugerida.
- Ativo opcional.
- Fonte.
- Confianca.
- Dados usados.

## Linguagem

O Guardian pode dizer:

- "precisa de acompanhamento"
- "revisar tese"
- "avaliar proximos aportes"
- "estudar reducao ou substituicao"

O Guardian nao deve dizer:

- "venda agora"
- "compre agora"
- "sem risco"
- "garantido"

