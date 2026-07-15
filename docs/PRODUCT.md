# Product - Carteira Alpha 360

Status: documento de produto vivo.

## Constituicao do produto

O documento `docs/CONSTITUICAO_DO_PROJETO.md` e a diretriz maxima de produto, arquitetura e engenharia do Carteira Alpha 360.

Toda decisao de produto deve responder ao principio central: a funcionalidade melhora de forma mensuravel a capacidade do usuario de construir patrimonio liquido de longo prazo e tomar decisoes financeiras melhores?

## Posicionamento

Carteira Alpha 360 e uma plataforma SaaS premium de inteligencia patrimonial para investidores que desejam acompanhar, entender e desenvolver patrimonio com clareza, disciplina e visao global.

Evolucao futura: alem de Wealth OS patrimonial, o produto passa a mirar uma vertical chamada `Alpha Premium Research`, voltada a research premium, carteira-modelo, edicoes mensais, newsletter, publicacao web/PDF e area de assinantes.

## Promessa do produto

Explicar a carteira, seus riscos, suas fontes de retorno, sua renda passiva, seus objetivos e seus desalinhamentos, sem prometer rentabilidade e sem emitir ordem direta de compra ou venda.

Promessa de entrada usada na autenticacao:

> Construa patrimonio. Tome decisoes melhores.

Subtexto:

> Carteira, research, estrategias, governanca, rastreabilidade e inteligencia patrimonial em uma unica plataforma.

## Usuarios alvo

- Investidor pessoa fisica que acompanha a propria carteira.
- Investidor que recebe dividendos e quer previsibilidade.
- Investidor que combina Brasil, exterior e cripto.
- Investidor de longo prazo que quer estrategia e disciplina.
- Futuramente, assessor, planejador ou multi-family office.

## Experiencia desejada

- Premium.
- Seria.
- Rapida.
- Confiavel.
- Institucional.
- Explicavel.
- Preparada para IA.
- Login e onboarding com sensacao de plataforma patrimonial robusta, sem expor detalhe tecnico antes do acesso.
- Landing de autenticacao com protagonismo de marca, fundo institucional, card reduzido e indicadores demonstrativos leves, sem parecer dashboard interno antes do login.

## Linguagem permitida

- Ativo atrativo.
- Ativo caro.
- Ativo descontado.
- Atencao ao risco.
- Bom para dividendos.
- Bom para crescimento.
- Fora dos criterios.
- Compativel com a estrategia.
- Desalinhado com o objetivo.

## Linguagem proibida

- Compre.
- Venda.
- Vai subir.
- Vai cair.
- Garantido.
- Sem risco.

## Modulos atuais

- Autenticacao.
- Visao Geral.
- Minha Carteira.
- Cripto.
- Dividendos.
- Crescimento.
- Radar de Ativos.
- Carteira Recomendada.
- Estrategias.
- Projecoes.
- Rebalanceamento.
- Alertas.
- Configuracoes.
- Alpha Intelligence Engine.
- Alpha Wealth OS.

## Vertical futura - Alpha Premium Research

O Alpha Premium Research deve ser uma plataforma viva de pesquisa patrimonial e publicacao institucional, nao apenas um PDF.

Experiencias previstas:

- plataforma premium com atualizacoes continuas;
- edicao mensal consolidada;
- carteira-modelo Alpha;
- teses versionadas;
- revisao mensal;
- research por ativo;
- performance attribution;
- publication readiness;
- snapshot imutavel de edicao;
- PDF e pagina web protegida;
- checkout de assinatura premium;
- distribuicao auditavel para assinantes;
- newsletter por e-mail;
- historico auditavel;
- controle de acesso por assinatura.

Regra de produto:

- O sistema gera analise, evidencias e rascunhos.
- A publicacao oficial depende de revisao e aprovacao humana.
- Nenhuma edicao deve esconder fallback, dado parcial, divergencia ou baixa confianca.
- Nenhum conteudo premium deve prometer rentabilidade ou virar ordem direta de compra/venda.
- Nenhum pagamento deve ativar acesso premium sem webhook/confirmacao backend e entitlement auditavel.
- Nenhuma edicao deve ser distribuida sem publicacao aprovada, PDF/artefato rastreavel e destinatario com acesso premium.

## Evolucao de produto

As telas atuais podem continuar existindo por clareza para o usuario. Internamente, porem, elas devem consumir engines universais:

- Minha Carteira consome Global Portfolio Engine.
- Dividendos consome Strategy Engine + Knowledge Engine.
- Crescimento consome Strategy Engine + Knowledge Engine.
- Cripto consome Asset Engine + Market Data Engine.
- Projecoes consome Wealth Builder.
- Visao Geral passa a consumir Alpha Wealth OS para centro de comando patrimonial.
- Carteira Recomendada consome Recommended Portfolio Engine, Alpha Confidence, screeners e Strategy Engine para entregar relatorio institucional mensal.
- Estrategias consome Strategy Engine 2.0 para mostrar aderencia a dividendos, crescimento, global, cripto controlado, aposentadoria e filosofias patrimoniais.
- Alertas consome Guardian.
- Copilot consome Knowledge, Portfolio, Strategy e Guardian.

## Alpha Wealth OS

O Alpha Wealth OS e a experiencia de produto que transforma o sistema em um cockpit patrimonial.

Na Visao Geral, ele deve responder rapidamente:

- Onde estou hoje?
- Qual minha missao atual?
- Quanto falta para as principais metas?
- Qual o risco que mais merece atencao?
- Quais oportunidades estao em estudo?
- Qual a confiabilidade dos dados usados?

Essa camada nao deve virar recomendacao direta. Ela deve orientar decisao com linguagem humana, dados internos e confianca declarada.

## Research & Evidence Center

O Research & Evidence Center deve responder:

- Por que esse ativo esta sendo acompanhado?
- Quais dados sustentam a leitura?
- Existem noticias recentes?
- Quais fontes estao fortes ou fracas?
- O que falta para aumentar a confianca?

Regra de produto: noticia nao e recomendacao. Noticia e evidencia para pesquisa, sempre cruzada com fundamentos, risco e objetivo patrimonial.

## Alpha Premium Research

A vertical premium deve transformar dados internos em edicoes auditaveis, revisadas e aprovadas antes de qualquer publicacao.

Entregas tecnicas atuais:

- Alpha Research Publisher para rascunhos estruturados.
- Thesis Engine para tese historica versionada por ativo.
- Rating Engine baseado em tese versionada.
- Research Committee para gates institucionais antes da revisao humana.
- Performance Attribution Engine para explicar retorno por ativo, preco, renda, benchmark e qualidade de dado.
- Publication Snapshot Engine para congelar edicoes aprovadas antes de PDF/web/distribuicao.
- Publication Render Engine para gerar HTML premium reproduzivel a partir do snapshot aprovado.
- Publication PDF Publisher para gerar PDF binario auditavel a partir do HTML aprovado.
- Premium Entitlements Engine para planos, assinaturas, permissoes e download de PDF protegido.
- Premium RBAC e Area Premium do Assinante para separar operador editorial de assinante final.
- Payment Gateway para checkout, webhook, transacao auditavel e ativacao de assinatura premium.
- Distribution Engine para campanhas, destinatarios, provider mock/local, providers externos preparados, templates premium e eventos de entrega.
- Notification Center para o assinante acompanhar edicoes recebidas, pendentes, abertas, clicadas e baixadas.
- API administrativa protegida e tela inicial `Research Premium`.

Regra de produto: uma publicacao premium nunca pode ser automatica. Ela precisa de evidencia, comite, revisao humana e aprovacao final.

## Strategy Engine 2.0

A tela Estrategias deve responder:

- Qual perfil patrimonial minha carteira mais segue hoje?
- Onde minha alocacao esta longe do alvo conceitual?
- Quais fatores estao fortes ou fracos?
- Quais ativos combinam com o perfil escolhido?
- O que devo estudar antes de rebalancear?

Regra de produto: estrategia nao e ordem. O sistema orienta estudo, disciplina e rebalanceamento consciente, sem frase de compra ou venda automatica.

## Regra de produto

O produto deve parecer uma plataforma financeira vendavel, mas a arquitetura deve ser mais sofisticada que a interface. A interface pode ser simples de usar; o nucleo nao pode ser simplista.
