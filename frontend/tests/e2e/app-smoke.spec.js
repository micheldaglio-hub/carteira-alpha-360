import { expect, test } from "@playwright/test";

test("login, dashboard, stress test and copilot smoke", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.locator(".auth-bg-image")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Construa patrimonio.*Tome decisoes melhores/i })).toBeVisible();
  await expect(page.getByText(/Teses versionadas/i)).toBeVisible();
  await expect(page.getByText(/Evidencias rastreaveis/i)).toBeVisible();
  await expect(page.getByText(/Imagem e metricas do fundo sao demonstrativas/i)).toBeVisible();
  await page.setViewportSize({ width: 1366, height: 768 });
  const compactLoginViewport = await page.evaluate(() => ({
    height: window.innerHeight,
    scrollHeight: document.documentElement.scrollHeight,
  }));
  expect(compactLoginViewport.scrollHeight).toBeLessThanOrEqual(compactLoginViewport.height + 2);
  await expect(page.getByLabel(/Manter conectado/i)).toBeChecked();
  await page.getByRole("button", { name: /Usar tema claro|Usar tema escuro/i }).click();
  await page.getByRole("tab", { name: /Cadastro/i }).click();
  await expect(page.getByLabel(/Nome completo/i)).toBeVisible();
  await page.getByRole("tab", { name: /Login/i }).click();
  await page.getByRole("button", { name: /Mostrar senha/i }).click();
  await expect(page.getByLabel("Senha", { exact: true })).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: /Ocultar senha/i }).click();
  await page.getByRole("button", { name: /Esqueci minha senha/i }).click();
  await expect(page.getByText(/Recuperacao de senha/i)).toBeVisible();

  await page.getByLabel("Email").fill("demo@carteiraalpha.com");
  await page.getByLabel("Senha", { exact: true }).fill("senha-incorreta");
  await page.getByRole("button", { name: /Acessar meu Wealth OS/i }).click();
  await expect(page.getByText(/Email ou senha invalidos/i)).toBeVisible();

  await page.getByLabel("Senha", { exact: true }).fill("Carteira@123");
  await page.getByRole("button", { name: /Acessar meu Wealth OS/i }).click();

  await expect(page.getByRole("heading", { name: /visao geral|visao geral/i })).toBeVisible();
  await expect(page.getByText(/Centro de Comando Patrimonial/i).first()).toBeVisible({ timeout: 30000 });

  await page.getByRole("button", { name: /Stress Test/i }).click();
  await expect(page.getByRole("heading", { name: /Teste de resistencia|Teste de resistencia/i })).toBeVisible();
  await expect(page.getByText(/Crise global|cenarios|cenarios/i).first()).toBeVisible();

  await page.locator('button[title="Copilot"]').evaluate((button) => button.click());
  await expect(page.getByRole("heading", { name: /Conversa patrimonial/i })).toBeVisible();
  await page.getByPlaceholder(/Pergunte/i).fill("Explique minha carteira e cite as fontes");
  await page.getByRole("button", { name: /Enviar/i }).click();
  await expect(page.getByText(/^S1$/).first()).toBeVisible();

  await page.locator('button[title="Sistema"]').evaluate((button) => button.click());
  await expect(page.getByRole("heading", { name: /Saude do sistema|Saude do sistema/i })).toBeVisible();
  await expect(page.getByText(/Auditoria/i).first()).toBeVisible();
});
