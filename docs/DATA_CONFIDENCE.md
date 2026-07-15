# Data Confidence Engine

Status: fundacao implementada em 2026-07-13.

## Objetivo

O Data Confidence Engine informa ao usuario e aos motores internos o quanto cada area de dados e confiavel.

Areas iniciais:

- Posicoes da carteira.
- Precos atuais.
- Setores e classes.
- Proventos.
- Cenario macro e fiscal.
- Cambio.

## Regra

Quando o dado estiver incompleto, o sistema deve dizer que esta incompleto. Ele nunca deve fingir certeza.

## Arquivo

- `backend/app/wealth_os/data_confidence_engine.py`
- `backend/app/wealth_os/macro_fx_engine.py`
