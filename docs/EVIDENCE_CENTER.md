# Evidence Center

Status: primeira versao implementada em 2026-07-13.

## Objetivo

O Evidence Center e a experiencia visual do Research & News Engine.

Ele aparece na tela `Carteira Recomendada Alpha` para mostrar:

- Cobertura de research.
- Quantidade de ativos analisados.
- Ativos com evidencias.
- Ativos com noticias.
- Saude das fontes.
- Cards de research por ativo.
- Feed de noticias monitoradas quando disponivel.

## Arquivo de frontend

- `frontend/src/pages/ModelPortfolios.jsx`

## Regra

O Evidence Center deve ser simples de ler para usuario leigo, mas sustentado por dados rastreaveis do backend.

O frontend nao calcula research score e nao consulta provider externo.

