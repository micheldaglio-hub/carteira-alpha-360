# Design System - Carteira Alpha 360

Status: documento vivo de identidade visual e experiencia.

## Identidade

O Carteira Alpha 360 usa uma identidade institucional de inteligencia patrimonial:

- preto e chumbo como base;
- dourado/amarelo como destaque principal;
- verde para sucesso;
- vermelho para risco/erro;
- azul apenas como apoio informacional;
- interfaces densas, serias e vendaveis.

## Landing de autenticacao

Arquivos:

- `frontend/src/pages/Login.jsx`
- `frontend/src/styles/index.css`
- `frontend/public/assets/alpha-login-background.webp`
- `frontend/public/assets/alpha-login-background.png`

Decisao visual:

- A tela de login deve parecer entrada de uma plataforma de inteligencia patrimonial, nao um dashboard interno.
- A imagem aprovada do Alpha 360 e o elemento visual principal.
- O formulario fica em card escuro translucido com blur seletivo apenas atras dele.
- O fundo deve continuar visivel, preservando mapa mundial, graficos, linhas douradas e sensacao global.
- Dados visuais do fundo sao tratados como demonstracao.

Polimento final:

- Nao trocar novamente a imagem de fundo sem decisao explicita de produto.
- O card de login deve ser menor que o peso visual do hero institucional.
- A marca completa deve aparecer no hero; o card pode usar apenas o icone e uma leitura de acesso seguro para evitar repeticao.
- Headline oficial: `Construa patrimonio. Tome decisoes melhores.`
- Os antigos elementos `Dados`, `Evidencias` e `Governanca` nao devem voltar como botoes decorativos.
- Indicadores institucionais devem ser demonstrativos, leves e claramente identificados como demonstracao.
- O login nunca deve parecer dashboard interno antes da autenticacao.

Overlays:

- camada preta translucida para contraste;
- gradiente escuro da esquerda para o centro;
- vinheta nas bordas;
- sem particulas ou animacoes pesadas.
- centro e lado direito devem revelar mapa, linhas douradas e graficos, desde que o contraste continue adequado.

Microinteracoes:

- fade-in no hero;
- slide-up discreto no card;
- glow suave no botao principal;
- hover e foco elegantes;
- respeito a `prefers-reduced-motion`.
- animacoes continuas devem ser lentas e restritas a transform, opacity ou background-position.

Responsividade:

- desktop: hero institucional e card lado a lado, imagem com presenca real;
- tablet: composicao em uma coluna, card com largura controlada;
- mobile: card ocupa quase toda a largura, textos secundarios reduzidos e sem scroll horizontal.
- em mobile, indicadores institucionais podem ser ocultados para preservar foco, contraste e velocidade.

Escala tipografica da landing:

- eyebrow: pequeno, uppercase, dourado, tracking alto;
- marca: uppercase, dourado, assinatura secundaria discreta;
- headline: peso alto, line-height curto, quebra intencional;
- subheadline: semibold, leitura clara;
- body/helper/legal: menor, mas nunca ilegivel;
- botao: peso alto, texto curto e direto.

## Regras permanentes

- Nao copiar identidade visual de corretoras, bancos ou plataformas existentes.
- Nao expor credenciais ou dados sensiveis na interface.
- Nao colocar regra de negocio no frontend.
- Manter tema claro e escuro compativeis com os tokens globais.
- Toda mudanca visual relevante deve atualizar este documento e o changelog.
