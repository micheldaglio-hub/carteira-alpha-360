# Alpha Copilot com IA

Status: Copilot conversacional implementado em 2026-07-13.

## Objetivo

O `Alpha Copilot` e a camada conversacional do Carteira Alpha 360.

Ele responde perguntas do usuario usando apenas dados internos consolidados pelo backend. Quando a IA externa estiver configurada, o LLM recebe um pacote de contexto interno com fontes numeradas. Quando a IA externa nao estiver configurada, o sistema usa fallback deterministico com as mesmas fontes internas.

## Principios

- O frontend nunca chama provider de IA diretamente.
- Tokens e chaves nunca sao enviados ao navegador.
- O Copilot nao busca dados crus em providers externos.
- O Copilot consome contexto consolidado por motores internos.
- Toda resposta deve declarar fontes internas usadas.
- Se faltar dado, a resposta deve declarar a lacuna.
- Nao pode prometer rentabilidade.
- Nao pode dizer "compre agora" ou "venda agora".
- Nao pode inventar preco, fundamento, noticia ou evento que nao esteja no contexto.

## Arquivos

- `backend/app/wealth_os/copilot_service.py`
- `backend/app/routers/wealth_os.py`
- `backend/app/wealth_os/contracts.py`
- `backend/app/schemas.py`
- `frontend/src/pages/Copilot.jsx`
- `frontend/src/components/Sidebar.jsx`
- `frontend/src/App.jsx`

## Endpoints

- `GET /api/wealth-os/copilot/questions`
- `GET /api/wealth-os/copilot/answer/{question_id}`
- `GET /api/wealth-os/copilot/status`
- `POST /api/wealth-os/copilot/chat`

Payload do chat:

```json
{
  "message": "Explique minha carteira e o maior risco agora",
  "conversation_id": "opcional"
}
```

Resposta:

```json
{
  "id": "...",
  "question": "...",
  "answer": "...",
  "confidence": "media",
  "mode": "ai",
  "provider": "openai",
  "citations": [
    {
      "id": "S1",
      "title": "Resumo consolidado da carteira",
      "source": "dashboard.metrics",
      "dataPath": "summary",
      "confidence": "alta",
      "excerpt": "..."
    }
  ],
  "followUps": [],
  "warnings": [],
  "dataUsed": ["summary"]
}
```

## Fontes internas

O contexto do Copilot pode incluir:

- `dashboard.metrics`
- `portfolio.positions`
- `goal_engine`
- `wealth_progress_score`
- `guardian`
- `data_confidence_engine`
- `strategy_engine`
- `scenario_engine`
- `economic_engine`

As fontes sao numeradas como `S1`, `S2`, `S3` etc. A IA deve citar essas fontes no texto.

## Configuracao

Variaveis:

```env
ALPHA_COPILOT_AI_ENABLED=false
ALPHA_COPILOT_PROVIDER=openai
ALPHA_COPILOT_MODEL=gpt-4o-mini
ALPHA_COPILOT_TIMEOUT_SECONDS=20
ALPHA_COPILOT_MAX_CONTEXT_CHARS=18000
ALPHA_COPILOT_API_KEY=
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
```

Regra:

- Se `ALPHA_COPILOT_AI_ENABLED=false`, o Copilot usa fallback interno.
- Se `ALPHA_COPILOT_AI_ENABLED=true` e houver chave, o backend chama o provider configurado.
- Se o provider falhar, o backend retorna fallback interno com aviso.

## Guardrails

O prompt do provider exige:

- Responder em portugues do Brasil.
- Usar somente `CONTEXTO_INTERNO`.
- Citar fontes no formato `[S1]`.
- Retornar JSON valido.
- Declarar incerteza quando faltar dado.
- Evitar recomendacao direta e promessa de resultado.

O backend ainda sanitiza termos proibidos como:

- `compre agora`
- `venda agora`
- `vai subir`
- `sem risco`
- `garantido`

## Testes

- `backend/tests/test_wealth_os.py`

Cobertura:

- Perguntas estruturadas antigas continuam funcionando.
- Chat usa fallback seguro quando IA externa nao esta configurada.
- Respostas trazem citacoes e `dataUsed`.
- Runtime status informa se a IA esta conectada ou se esta usando fallback.
