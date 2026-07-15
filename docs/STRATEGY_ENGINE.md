# Strategy Engine 2.0

Status: implementado em 2026-07-13.

## Objetivo

O Strategy Engine 2.0 interpreta a carteira do usuario contra diferentes estilos de construcao patrimonial.

Ele nao executa ordens, nao promete retorno e nao troca ativos sozinho. A funcao e responder:

- Qual perfil patrimonial a carteira mais parece seguir.
- Onde existe aderencia ou desalinhamento.
- Qual alocacao alvo conceitual combina com cada perfil.
- Quais fatores precisam de estudo antes de rebalancear.
- Quais ativos combinam mais com o perfil selecionado.

## Arquivos

- `backend/app/wealth_os/strategy_engine.py`
- `backend/app/wealth_os/contracts.py`
- `backend/app/routers/wealth_os.py`
- `backend/app/wealth_os/service.py`
- `frontend/src/pages/Strategies.jsx`
- `frontend/src/components/Sidebar.jsx`
- `frontend/src/App.jsx`
- `backend/tests/test_strategy_engine.py`

## Endpoint

`GET /api/wealth-os/strategies`

Retorna um `StrategyEngineReport` com:

- `status`
- `headline`
- `primaryStrategy`
- `primaryScore`
- `currentAllocation`
- `metrics`
- `assessments`
- `rules`
- `updatedAt`

O endpoint e autenticado e sempre usa dados internos da carteira do usuario.

## Perfis implementados

- Dividendos.
- Crescimento.
- Global.
- Cripto Controlado.
- Aposentadoria.
- Barsi.
- Buffett.
- Bogle.
- Dalio.
- Lynch.

Cada perfil possui:

- Nome.
- Arquetipo.
- Descricao.
- Perfil de risco.
- Horizonte.
- Filosofia.
- Alocacao alvo.
- Pesos de avaliacao.
- Setores e classes preferidos.
- Limites de cripto, ativo e setor.

## Classes universais usadas

O motor normaliza os ativos em buckets estrategicos:

- `Acoes Brasil`
- `FIIs`
- `ETFs`
- `Global`
- `Cripto`
- `Caixa/Renda Fixa`
- `Outros`

A normalizacao considera classe, subclasse, setor, moeda, pais, regiao e mercado. Assim, uma stock em USD ou NASDAQ entra como `Global`, enquanto uma cripto entra como `Cripto`.

## Fatores de score

Cada estrategia calcula:

- Alocacao por classe.
- Renda passiva.
- Concentracao.
- Diversificacao.
- Exposicao global.
- Cripto controlado.
- Qualidade setorial.

O score final e a media ponderada dos fatores definidos em cada perfil.

## Linguagem permitida

O motor pode dizer:

- "A carteira combina mais com Dividendos."
- "A carteira tem aderencia parcial ao perfil Global."
- "Estudar proximos aportes para aproximar Global do perfil."
- "Acompanhar sobrepeso em Cripto."
- "Revisar concentracao do maior ativo antes de aumentar exposicao nele."

O motor nao deve dizer:

- "Compre agora."
- "Venda agora."
- "Esse ativo vai subir."
- "Rentabilidade garantida."
- "Pode comprar sem medo."

## Interface

A aba `Estrategias` exibe:

- Perfil dominante.
- Score de aderencia.
- Exposicao global.
- Peso de cripto.
- Peso do maior ativo.
- Ranking completo de estrategias.
- Grafico atual versus alvo.
- Fatores do perfil selecionado.
- Filosofia em linguagem humana.
- Proximos estudos.
- Encaixe dos ativos.
- Regras do motor.

## Integracoes futuras

O Strategy Engine 2.0 foi criado para alimentar:

- Rebalanceamento inteligente.
- Guardian.
- Alertas.
- Wealth Builder.
- Alpha Copilot.
- Carteira Recomendada.
- Alpha Score Mundial.

## Testes

`backend/tests/test_strategy_engine.py` valida:

- Criacao do relatorio sem depender da interface.
- Presenca dos perfis principais.
- Normalizacao de ativo global e cripto.
- Fatores, asset fits e leituras estruturadas.

## Criterios de aceite

- O motor funciona apenas com dados internos.
- Nenhuma rota antiga foi alterada.
- Nenhum payload antigo foi quebrado.
- A tela nova consome endpoint proprio.
- O sistema continua funcional se nao houver ativo suficiente; nesse caso os scores tendem a zero.
- Toda leitura e explicavel e nao automatiza decisao de compra ou venda.
