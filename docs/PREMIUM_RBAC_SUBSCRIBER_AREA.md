# Premium RBAC e Area do Assinante

Status: fundacao tecnica implementada em 2026-07-14.

## Objetivo

Separar usuario operacional de assinante premium.

RBAC define o que o usuario pode operar no sistema. Entitlements definem o que o assinante pode acessar como produto pago.

## Arquivos

- `backend/app/services/rbac.py`
- `backend/alembic/versions/20260714_0017_user_roles_rbac.py`
- `backend/app/routers/premium.py`
- `backend/app/routers/auth.py`
- `frontend/src/pages/PremiumSubscriber.jsx`
- `frontend/src/components/Sidebar.jsx`
- `frontend/src/App.jsx`
- `backend/app/routers/billing.py`
- `backend/app/billing/gateway.py`

## Tabela

- `user_roles`

Campos principais:

- `user_id`
- `role`
- `scope_type`
- `scope_id`
- `status`
- `source`
- `granted_by_user_id`
- `starts_at`
- `expires_at`

## Papeis

- `admin`: controla toda a vertical premium.
- `editor`: cria rascunhos, roda motores, gera snapshot, HTML e PDF.
- `reviewer`: registra revisao humana.
- `premium_subscriber`: acessa area premium e conteudo liberado por assinatura ativa.
- `free_user`: papel basico para novos usuarios.

## Regras

- Usuarios existentes recebem `admin` no backfill da migration para preservar acesso ao sistema local.
- Novos usuarios recebem `free_user` no cadastro/login se ainda nao possuirem papel.
- `Research Premium` e area editorial exigem `admin`, `editor` ou `reviewer`.
- Aprovacao final exige `admin` ou `editor`.
- Revisao humana exige `admin` ou `reviewer`.
- Gestao de assinatura e concessao de papeis exige `admin`.
- Download de PDF premium continua exigindo dono editorial/admin ou entitlement ativo.

## APIs novas

```text
GET  /api/premium/rbac/me
POST /api/premium/rbac/roles/grant
GET  /api/premium/subscriber/home
```

APIs alteradas:

```text
POST /api/premium/subscriptions/grant
```

Agora exige `admin` e aceita `user_id` opcional para conceder assinatura a outro usuario.

## Frontend

Nova pagina:

- `Area Premium`

Ela mostra:

- plano atual;
- planos pagos disponiveis;
- botoes de assinatura mensal/anual;
- papeis RBAC;
- permissoes ativas;
- uso de downloads;
- edicoes aprovadas;
- PDFs disponiveis;
- logs recentes de acesso.

O checkout e criado pelo backend via `Payment Gateway`. Em ambiente local, o provider `mock` permite ativar uma assinatura de teste sem cartao. Em producao, a mesma tela deve consumir um provider externo configurado no backend.

O menu `Research Premium` fica visivel apenas para usuarios editoriais.

## Compatibilidade

- Nenhum calculo financeiro foi alterado.
- Nenhum payload legado foi removido.
- Migration aditiva com rollback seguro para `20260714_0016`.
- Area do assinante usa endpoints novos e nao reaproveita a tela administrativa.

## Testes

- Testes premium foram atualizados para conceder papel `admin` explicitamente.
- Teste de assinatura valida que usuario comum nao consegue conceder assinatura para si mesmo.
- Teste de area do assinante valida acesso a edicao/PDF quando a assinatura esta ativa.
