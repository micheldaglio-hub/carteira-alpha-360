# Screener Alpha B3

Status: primeira versao implementada em 2026-07-11.

## Objetivo

O Screener Alpha B3 e o modulo responsavel por gerar a `Carteira Recomendada Alpha oficial` a partir de uma leitura propria do Carteira Alpha 360.

Ele substitui a carteira principal importada dos relatorios antigos como fonte da tela `Carteira Recomendada`.

## Arquivo principal

- `backend/app/services/alpha_b3_screener.py`

## Rotas

- `GET /api/model-portfolios/screener`
- `POST /api/model-portfolios/screener/run`

## Responsabilidades

- Ler o universo de tickers B3 via BRAPI quando a API estiver disponivel.
- Filtrar instrumentos que nao fazem parte da tese central de acoes brasileiras.
- Avaliar candidatas de setores perenes.
- Enriquecer fundamentos pelo Market Data Engine quando o usuario manda atualizar a analise.
- Gerar ranking interno Alpha.
- Gerar a carteira oficial com pesos-alvo.
- Explicar tese, papel na carteira e pontos de acompanhamento.

## Funil inicial

1. Universo bruto B3.
2. Elegibilidade de ticker de acao local.
3. Foco em setores perenes: energia, saneamento, seguros, bancos, holding financeira e telecom.
4. Candidatas fundamentalistas com leitura qualitativa e quantitativa.
5. Selecionadas finais da carteira oficial.

## Carteira Recomendada Alpha oficial

Versao atual: 2026-07-11.

- BBSE3: 13%.
- TAEE11: 12%.
- ITSA4: 11%.
- BBAS3: 10%.
- EGIE3: 10%.
- CPFE3: 9%.
- SAPR11: 9%.
- PSSA3: 8%.
- VIVT3: 8%.
- CSMG3: 10%.

Total: 100%.

## Metricas usadas

O score combina:

- Qualidade qualitativa do negocio.
- Liquidez.
- Governanca.
- Estabilidade setorial.
- Risco qualitativo.
- Score de dividendos, quando houver dados.
- Score de seguranca, quando houver dados.
- Score de valuation, quando houver dados.
- Score de risco quantitativo, quando houver dados.

Quando dados quantitativos externos estiverem incompletos, o Screener usa a leitura estrategica como camada primaria e registra quantos campos reais estavam disponiveis. A mistura quantitativa completa so entra quando ha cobertura suficiente de fundamentos, evitando que poucos campos soltos derrubem artificialmente uma empresa defensiva.

## Fontes de dados

- BRAPI para universo B3 e dados de mercado quando disponivel.
- Market Data Engine v2 para enriquecimento multi-provider.
- Providers futuros ou opcionais: Dados de Mercado, FMP, Twelve Data, Fundamentus, CVM, B3 e outros.

Regra: o frontend nunca consulta provider externo diretamente.

## Exclusoes relevantes da carteira antiga

- BBDC4 ficou fora do nucleo por ainda depender de recuperacao clara de rentabilidade.
- BRSR6 ficou fora por risco politico/regional e menor liquidez relativa.
- AURE3 ficou fora por menor previsibilidade de dividendos.
- CPLE6 ficou fora por perder prioridade para TAEE11, EGIE3 e CPFE3 na composicao atual.

## Guardrails

- Nao prometer rentabilidade.
- Nao emitir ordem operacional de compra ou venda.
- Usar a carteira como modelo Alpha oficial, com revisao mensal.
- Explicar riscos e pontos de acompanhamento.
- Atualizar documentacao sempre que pesos, criterios ou componentes mudarem.

## Evolucao prevista

- Incluir ranking completo com todas as empresas elegiveis da B3 quando os providers entregarem fundamentos historicos em massa.
- Persistir rodadas de screener no banco.
- Adicionar historico de mudancas de pesos.
- Comparar carteira recomendada contra carteira real do usuario.
- Integrar com Strategy Engine e Knowledge Engine.
