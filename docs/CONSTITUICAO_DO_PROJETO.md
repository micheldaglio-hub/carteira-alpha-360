# Constituicao Oficial do Projeto - Carteira Alpha 360

Status: documento permanente de arquitetura, engenharia e produto.

Este documento e a diretriz maxima do Carteira Alpha 360. Toda decisao arquitetural, tecnica, matematica, estatistica, visual, funcional e de produto deve ser compativel com esta Constituicao.

Quando houver conflito entre uma decisao local e este documento, este documento prevalece. A decisao local deve ser reavaliada, documentada ou rejeitada.

## Missao

O Carteira Alpha 360 existe para ajudar o usuario a construir patrimonio de longo prazo de maneira consistente, inteligente e sustentavel.

Todo modulo, algoritmo, tela, calculo, integracao, inteligencia artificial, analise ou funcionalidade deve contribuir direta ou indiretamente para esse objetivo.

O sucesso da plataforma sera medido pela qualidade das decisoes que ela ajuda o usuario a tomar e pela capacidade de acompanhar, organizar e evoluir seu patrimonio ao longo dos anos.

## Proposito

O Carteira Alpha 360 nao e apenas um gerenciador de investimentos.

Ele e uma plataforma de inteligencia patrimonial.

Seu proposito e reunir em um unico sistema as ferramentas necessarias para estudar ativos, organizar patrimonio, acompanhar riscos, analisar empresas, comparar investimentos, projetar cenarios e apoiar decisoes financeiras de longo prazo.

## Filosofia

A plataforma deve sempre privilegiar:

- Crescimento consistente.
- Preservacao de patrimonio.
- Renda passiva crescente.
- Diversificacao inteligente.
- Gestao de risco.
- Qualidade dos ativos.
- Analise baseada em dados.

A plataforma nunca deve privilegiar apostas, especulacao, promessas de ganhos rapidos ou estrategias incompativeis com uma construcao patrimonial solida.

## Principio Maximo

Antes de qualquer implementacao, o sistema deve responder a seguinte pergunta:

> Esta funcionalidade melhora de forma mensuravel a capacidade do usuario de construir patrimonio liquido de longo prazo e tomar decisoes financeiras melhores?

Se a resposta for negativa, a implementacao deve ser reavaliada.

## Papel da IA

A inteligencia artificial da plataforma deve atuar como um analista patrimonial permanente, baseado em dados tratados pelo sistema.

Ela deve ser preparada para:

- Estudar empresas, setores, paises, moedas e bolsas mundiais.
- Estudar renda fixa, FIIs, REITs, ETFs, commodities e criptomoedas.
- Estudar indicadores macroeconomicos, fundamentos, valuation, crescimento, dividendos e riscos.
- Avaliar qualidade dos ativos e deterioracao ou melhora de fundamentos.
- Identificar oportunidades de estudo e riscos relevantes.
- Explicar claramente seus raciocinios.

A IA nunca deve agir como geradora de palpites. Ela deve funcionar como mecanismo de analise, explicacao e apoio a decisao, sem emitir recomendacao direta de compra ou venda.

## Visao de Longo Prazo

O Carteira Alpha 360 deve evoluir continuamente para se tornar uma plataforma global de inteligencia patrimonial.

Ele deve ser preparado para analisar:

- Acoes brasileiras, americanas, europeias e asiaticas.
- ETFs, FIIs e REITs.
- Criptomoedas.
- Ouro, prata e commodities.
- Renda fixa, titulos publicos, bonds, caixa e futuros ativos financeiros.

Toda arquitetura deve permitir expansao sem reescrita estrutural do sistema.

## Plataforma de Research Premium

Como extensao futura do Wealth OS, o Carteira Alpha 360 podera evoluir para uma plataforma premium de pesquisa patrimonial, carteira-modelo, publicacao editorial, newsletter, PDF/web e area de assinantes.

Essa vertical deve obedecer aos mesmos principios da plataforma:

- dados rastreaveis;
- metodologia documentada;
- evidencias verificaveis;
- governanca;
- revisao humana;
- versionamento;
- transparencia de riscos;
- linguagem responsavel.

Nenhuma publicacao editorial, carteira-modelo premium, tese ou relatorio podera ser publicado automaticamente sem aprovacao humana explicita.

A IA podera apoiar rascunhos, explicacoes e resumo de dados, mas nao podera inventar numeros, ocultar lacunas, aprovar publicacao, alterar decisoes ou substituir compliance humano.

## Padrao de Engenharia

Toda implementacao deve seguir:

- Clean Architecture.
- SOLID.
- Baixo acoplamento.
- Alta coesao.
- Escalabilidade.
- Testes automatizados.
- Documentacao obrigatoria.
- Compatibilidade retroativa.
- Preparacao para PostgreSQL, Supabase e ambiente cloud.

Nenhuma regra financeira deve permanecer na interface React. Toda logica financeira, patrimonial, estatistica ou analitica deve estar centralizada em engines especificas.

## Padrao de Dados

Sempre que possivel, utilizar dados provenientes de fontes oficiais ou reconhecidas, como CVM, B3, BRAPI, APIs internacionais, CoinGecko, CoinMarketCap e outras fontes oficiais ou institucionais.

Sites de consulta complementar, como Fundamentus, podem ser usados apenas para validacao, comparacao ou enriquecimento. Eles nunca devem ser a unica fonte de verdade de uma metrica critica.

## Plataforma Global

O sistema deve ser preparado para trabalhar com:

- Multiplas moedas.
- Multiplos paises.
- Multiplas bolsas.
- Multiplos provedores.
- Multiplas classes de ativos.

O patrimonio deve sempre poder ser consolidado em uma visao unica, com rastreabilidade de origem, moeda, classe, mercado e provider.

## Motores Oficiais

Toda inteligencia deve ser organizada em engines independentes, cada uma com responsabilidade unica:

- Asset Engine.
- Market Data Engine.
- Knowledge Engine.
- Strategy Engine.
- Financial Projection Engine.
- FX Engine.
- Global Portfolio Engine.
- Alpha Score Engine.
- Wealth Builder.
- Guardian.
- Alpha Copilot.

Telas e componentes de interface devem consumir servicos e engines. Eles nao devem conter regras financeiras de dominio.

## Evolucao Continua

Sempre que uma nova metodologia, indicador, tecnologia, algoritmo, modelo estatistico ou fonte de dados aumentar a qualidade das analises patrimoniais, sua incorporacao deve ser considerada.

A arquitetura nunca deve impedir evolucao futura.

## Referencias de Mercado

O Carteira Alpha 360 nao deve copiar nenhuma plataforma existente.

Sua missao e reunir e superar, de forma integrada, as melhores capacidades encontradas em plataformas como Fundamentus, Status Invest, TradingView, Koyfin, Morningstar, Yahoo Finance, Bloomberg, Portfolio Visualizer, Finviz, Seeking Alpha, CoinMarketCap e CoinGecko.

O objetivo e oferecer uma experiencia unificada e superior, com identidade propria.

## Qualidade

Nenhuma funcionalidade deve ser implementada apenas por estetica.

Toda funcionalidade deve possuir proposito claro, impacto mensuravel e valor real para a gestao patrimonial.

Sempre priorizar qualidade em vez de quantidade.

## Documentacao

Toda alteracao relevante deve obrigatoriamente atualizar:

- `docs/DOCUMENTACAO_TECNICA.md`
- `CHANGELOG.md`

Quando necessario, novos documentos especificos devem ser criados ou atualizados.

O projeto deve permanecer totalmente documentado para que qualquer engenheiro consiga assumir seu desenvolvimento no futuro.

## Regra Final

O Carteira Alpha 360 deve ser construido como uma plataforma de inteligencia patrimonial de nivel mundial.

Toda decisao tecnica deve priorizar qualidade, confiabilidade, transparencia, escalabilidade e sustentabilidade.

O objetivo permanente do projeto e ajudar o usuario a construir patrimonio de longo prazo por meio de decisoes cada vez mais bem fundamentadas, utilizando dados, analise quantitativa, fundamentos, gestao de risco e melhoria continua.

Nenhuma implementacao pode contrariar esta missao.
