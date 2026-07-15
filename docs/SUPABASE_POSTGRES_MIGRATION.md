# Supabase / PostgreSQL Migration

Status: fundacao tecnica implementada em 2026-07-13.

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
- `DATABASE_AUTO_CREATE_TABLES=false` deve ser usado em producao.
- Copia de dados so ocorre com `-Apply`.
- Limpeza do destino so ocorre com `-Truncate`, e deve ser usada apenas com backup confirmado.
- Secrets reais nunca devem ser gravados em arquivos versionados.

## Fluxo recomendado

1. Copiar `.env.supabase.example` para `.env`.
2. Trocar `SUA_SENHA` pela senha real do Supabase.
3. Rodar dry-run estrutural:

```powershell
.\scripts\migrate-to-supabase.ps1 -SupabaseDatabaseUrl "postgresql://postgres:SENHA@db.stuzfrmukuabaularmtb.supabase.co:5432/postgres"
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

