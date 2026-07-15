# Data Confidence Engine V2

## Objetivo

O `Data Confidence Engine V2` mede se os numeros usados pelo Alpha possuem fonte rastreavel. Ele nao diz se um ativo e bom ou ruim; ele diz se o dado usado para analisar o ativo e confiavel o bastante.

## Campos auditados

- Preco atual
- Historico de precos
- Fundamentos
- Proventos/JCP
- Movimentacoes do usuario
- Divergencias entre fontes

## Saida principal

Cada ativo recebe:

- `score`: nota de 0 a 100
- `classification`: classificacao humana
- `hasFallback`: indica se algum campo depende de fallback/manual/cache incompleto
- `fieldAudits`: auditoria campo a campo
- `mainLimitation`: principal ponto fraco

## Uso no sistema

- Backtest da carteira atual: mostra cobertura e fallback.
- Carteira Recomendada: reduz conviccao quando a confianca de dados e baixa.
- Governanca: registra se uma tese pode ser elevada ou se precisa aguardar dados melhores.

## Arquivo principal

- `backend/app/services/data_confidence_engine.py`

