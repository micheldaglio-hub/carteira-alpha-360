# Carteira Alpha 360

Sistema SaaS web para acompanhamento e analise de carteira de investimentos, com foco em acoes, FIIs, ETFs, dividendos, crescimento patrimonial, projecao financeira e rebalanceamento.

Tambem possui modulo Cripto 360 para registrar aportes em criptomoedas, consolidar patrimonio total e acompanhar cotacao por provider dedicado.

## Stack

- Backend: Python, FastAPI, SQLAlchemy
- Banco: PostgreSQL via Docker Compose, Alembic para migracoes e fallback SQLite para preview local
- Frontend: React, Vite, TailwindCSS, Recharts
- Arquitetura: multiusuario, REST API, camada de providers de mercado substituivel

## Login demo

- Email: `demo@carteiraalpha.com`
- Senha: `Carteira@123`

## Caminho do projeto

`C:\Users\miche\OneDrive\Documentos\CarteiraAlpha`

## Abrir no dia a dia

Use o atalho `Carteira Alpha 360` criado na Area de Trabalho. Ele sobe backend e frontend, descobre o IP atual da maquina e abre o navegador.

URL fixa neste computador:

```text
http://127.0.0.1:5173
```

`127.0.0.1` nao muda. Se essa pagina recusar conexao, significa que os servidores nao estao rodando; o atalho ou o script abaixo corrige isso:

```powershell
.\scripts\start-carteira-alpha.ps1
```

O Windows tambem possui um atalho de inicializacao chamado `Carteira Alpha 360 Servidor`, que sobe o sistema automaticamente ao entrar no Windows.

## Rodar manualmente em modo desenvolvimento

Em dois terminais PowerShell:

```powershell
.\scripts\run-backend.ps1
```

```powershell
.\scripts\run-frontend.ps1
```

Os scripts tentam usar Python/Node do sistema. Se nao encontrarem, usam o runtime empacotado do Codex quando disponivel.

## Acessar pelo celular ou outro computador da mesma rede

Use o arquivo `INICIAR_CARTEIRA_ALPHA_REDE.bat` na raiz do projeto. Ele sobe o sistema e mostra as URLs atuais.

Na primeira vez, execute tambem `CONFIGURAR_ACESSO_REDE_ADMIN.bat`. O Windows vai pedir permissao de administrador para liberar somente a rede local nas portas `5173` e `8000`.

Para diagnosticar qualquer falha, use `DIAGNOSTICAR_ACESSO_REDE.bat`.

Fluxo manual:

1. Rode `.\scripts\start-carteira-alpha.ps1` ou use o atalho da Area de Trabalho.
2. Abra o arquivo gerado automaticamente:

```powershell
notepad .\logs\carteira-alpha-urls.txt
```

3. Em outro dispositivo conectado ao mesmo Wi-Fi/rede, tente primeiro o IP atual mostrado no arquivo:

```text
http://192.168.0.102:5173
```

4. Se quiser testar por nome do computador, use:

```text
http://MICHEL-PCGAMER:5173
```

O frontend usa automaticamente `http://HOST_ATUAL:8000/api` para falar com o backend. O backend aceita localhost, IPs privados e o nome local do computador em modo desenvolvimento.

Se outro computador ainda nao abrir depois disso, confirme se ele esta na mesma faixa de IP do PC principal. Exemplo: se este PC esta em `192.168.0.102`, o outro aparelho tambem precisa estar em `192.168.0.x`. Se estiver em `192.168.1.x` ou outra faixa, o segundo roteador esta isolando a rede; configure esse roteador como Bridge/AP ou desative isolamento de clientes.

## Rodar com PostgreSQL

1. Copie `.env.example` para `.env`.
2. Suba o banco:

```powershell
docker compose up -d postgres
```

3. Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

4. Frontend:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

5. Acesse: http://127.0.0.1:5173

## Modo producao seguro

Para preparar um ambiente que possa ser avaliado como produto SaaS, use `.env.production.example` como base.

Regras obrigatorias:

- `ENVIRONMENT=production`
- `SECRET_KEY` longo, unico e fora do codigo
- PostgreSQL em `DATABASE_URL`
- `SEED_DEMO_DATA=false`
- `MARKET_DATA_PROVIDER` diferente de `mock`
- CORS restrito ao dominio oficial

O backend agora possui um gate de seguranca: se `ENVIRONMENT=production` estiver ativo com segredo padrao, SQLite, dados demo ou provider mock, a aplicacao nao sobe.

Verificacao operacional:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/ready
```

Detalhes em `docs/PRODUCTION_READINESS.md`.

## Operacao, auditoria e backups

A aba `Operacoes` mostra observabilidade, requests recentes, auditoria e jobs operacionais.

Endpoints principais:

- `GET /api/ops/observability`
- `GET /api/ops/audit`
- `GET /api/ops/jobs`

Backup local ou PostgreSQL/Supabase:

```powershell
.\scripts\backup-database.ps1
```

Restore exige confirmacao explicita:

```powershell
.\scripts\restore-database.ps1 -BackupPath .\backups\arquivo.dump -ConfirmRestore
```

Teste E2E:

```powershell
cd frontend
pnpm run e2e
```

Deploy containerizado:

```powershell
docker compose -f docker-compose.prod.yml --env-file .env.production up --build
```

Detalhes em `docs/PRODUCTION_OBSERVABILITY_AUDIT.md`.

## Preview sem Docker

Se voce ainda nao tiver Docker/PostgreSQL instalado, crie `.env` com:

```env
DATABASE_URL=sqlite:///./carteira_alpha.db
SEED_DEMO_DATA=true
```

O backend criara o banco local e carregara dados mockados para teste.

## Migracoes de banco

O projeto usa Alembic como trilho oficial para evoluir o schema do banco sem depender de criacao manual de tabelas.

Para um banco novo:

```powershell
.\scripts\db-migrate.ps1
```

Para um banco local que ja foi criado antes da entrada do Alembic, marque o schema atual como baseline uma unica vez:

```powershell
.\scripts\db-stamp-head.ps1
```

Depois disso, novas alteracoes de modelos devem gerar uma nova revision Alembic e rodar `.\scripts\db-migrate.ps1`.

## Camada de dados externos

Os providers ficam em `backend/app/services/market_data/providers`.

- `MockMarketDataProvider`: dados de demonstracao.
- `BrapiMarketDataProvider`: estrutura preparada para cotacoes/fundamentos via API externa.
- `CoinMarketCapProvider`: cotacoes de criptomoedas quando `COINMARKETCAP_API_KEY` esta configurada.
- `CvmPublicDataProvider`: estrutura preparada para dados publicos da CVM.
- `B3PublicDataProvider`: estrutura preparada para dados publicos da B3.

Troque o provider com a variavel `MARKET_DATA_PROVIDER`.

## Cripto 360

Use o menu lateral `Cripto` para registrar compra/venda de criptomoedas com simbolo, quantidade, preco, taxa, exchange/corretora e wallet opcional.

As criptos entram no patrimonio total e na alocacao por classe, mas nao entram na renda passiva projetada nem no Radar de Dividendos. A cotacao automatica usa CoinMarketCap quando a variavel abaixo existir no `.env`:

```env
COINMARKETCAP_API_KEY=sua_chave_aqui
```

Depois de alterar `.env`, reinicie o backend e use o botao `Atualizar CoinMarketCap` na aba `Cripto`.

## Aviso

A plataforma nao promete rentabilidade e nao emite recomendacao de compra ou venda. As classificacoes usam termos analiticos como ativo atrativo, ativo caro, ativo descontado, atencao ao risco, bom para dividendos, bom para crescimento e fora dos criterios.

## Documentacao tecnica

A documentacao tecnica viva esta em `docs/DOCUMENTACAO_TECNICA.md`.

Regra do projeto: toda alteracao relevante em modelos, endpoints, calculos, providers, interface, scripts ou regras de negocio deve atualizar essa documentacao no mesmo ciclo de trabalho.
