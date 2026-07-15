# Supabase / PostgreSQL Migration

Status: fundacao tecnica implementada em 2026-07-13. Primeira migracao real validada em 2026-07-15.

## Objetivo

Migrar o Carteira Alpha 360 do SQLite local para PostgreSQL/Supabase sem apagar dados atuais, sem alterar payloads das APIs e sem depender de `create_all` em producao.

## Arquivos

- `scripts/migrate-to-supabase.ps1`
- `scripts/migrate_sqlite_to_postgres.py`
- `.env.supabase.example`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/core/runtime_safety.py`

## Regras de seguranca

- O script nao aceita connection string com placeholder de senha.
- Antes da migracao, o SQLite local e copiado para `backups/`.
- O schema do destino e criado/atualizado via Alembic.
- Em redes onde o Direct Connection do Supabase resolver apenas por IPv6, use o Session Pooler.
- `DATABASE_AUTO_CREATE_TABLES=false` deve ser usado em producao.
- Copia de dados so ocorre com `-Apply`.
- Limpeza do destino so ocorre com `-Truncate`, e deve ser usada apenas com backup confirmado.
- Secrets reais nunca devem ser gravados em arquivos versionados.
- O migrador valida chaves estrangeiras antes da copia e pula linhas historicas orfas que o SQLite permitia, mas que o PostgreSQL bloqueia corretamente.

## Fluxo recomendado

1. Copiar `.env.supabase.example` para `.env`.
2. Trocar `SUA_SENHA` pela senha real do Supabase.
3. Rodar dry-run estrutural:

```powershell
.\scripts\migrate-to-supabase.ps1 -SupabaseDatabaseUrl "postgresql://postgres:SENHA@db.stuzfrmukuabaularmtb.supabase.co:5432/postgres"
```

Quando usar Session Pooler, a URL segue o formato:

```powershell
.\scripts\migrate-to-supabase.ps1 -SupabaseDatabaseUrl "postgresql://postgres.PROJECT_REF:SENHA@aws-1-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require"
```

4. Se Alembic e auditoria passarem, copiar dados:

```powershell
.\scripts\migrate-to-supabase.ps1 -SupabaseDatabaseUrl "postgresql://postgres:SENHA@db.stuzfrmukuabaularmtb.supabase.co:5432/postgres" -Apply
```

5. Usar `-Truncate` somente para ambientes vazios ou recriados:

```powershell
.\scripts\migrate-to-supabase.ps1 -SupabaseDatabaseUrl "postgresql://postgres:SENHA@db.stuzfrmukuabaularmtb.supabase.co:5432/postgres" -Apply -Truncate
```

## Validacao

Ao final do fluxo, o script executa `Financial Formula Auditor`. Se a auditoria matematica falhar, a migracao operacional deve ser considerada bloqueada ate correcao.

## Execucao validada em 2026-07-15

- Origem: `backend/carteira_alpha.db`.
- Destino: Supabase PostgreSQL via Session Pooler.
- Alembic aplicado ate `20260714_0019`.
- Dados copiados com `-Apply -Truncate` apos tentativa parcial controlada.
- `Financial Formula Auditor`: `pass`, score `100.0`.
- Linhas puladas: 30 registros antigos de `asset_facts` com `asset_id` sem ativo correspondente em `assets`.
- Diferencas esperadas pos-migracao: `audit_events` e `data_evidence_ledger` podem ter mais registros no Supabase porque a auditoria pos-migracao grava evidencias reais no destino.
