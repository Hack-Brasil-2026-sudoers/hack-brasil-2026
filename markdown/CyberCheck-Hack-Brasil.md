# CyberCheck

**Hack Brasil / Cibersegurança**

Diagnóstico preventivo de segurança web

> Ideia candidata em avaliação, ainda sem seleção pelo grupo

## Contexto e problema

Pequenos negócios dependem de sites e sistemas para vender, atender clientes e operar. Muitos têm orçamento restrito e carecem de equipe dedicada, o que dificulta contratar uma avaliação de segurança e decidir quais falhas corrigir primeiro.

**Justificativa.** Uma hipótese é que aplicações criadas rapidamente com apoio de IA, prática conhecida como *vibe coding*, possam chegar ao ar com falhas quando a revisão e os testes são abreviados. A hipótese deve ser avaliada caso a caso.

### Público-alvo preferencial

Micro e pequenas empresas com aplicações web próprias ou sob sua administração, como lojas virtuais, portais de clientes e sistemas de agendamento.

### Proposta do serviço

Oferecer um diagnóstico inicial rápido e relativamente acessível, com apoio de uma equipe para interpretar os resultados e orientar as primeiras correções.

## Como funciona o serviço assistido

1. **Solicitação**  
   A empresa indica o site ou sistema que deseja avaliar.

2. **Autorização por escrito e escopo**  
   O responsável autoriza os sistemas e as verificações permitidas.

3. **Verificações automatizadas**  
   A equipe realiza verificações defensivas dentro do escopo autorizado.

4. **Validação humana**  
   A equipe revisa evidências, filtra falsos positivos e distingue alertas de achados confirmados.

5. **Relatório**  
   A empresa recebe um diagnóstico claro com impacto, prioridades e correções recomendadas.

6. **Acompanhamento opcional**  
   A empresa pode solicitar nova verificação após as correções.

## MVP, limites e validações

### MVP demonstrável

O protótipo registra uma solicitação, documenta a autorização e o escopo, executa verificações defensivas em uma aplicação web própria ou autorizada por escrito e gera um relatório com achados revisados, prioridades e correções sugeridas.

**Ferramentas possíveis.** ZAP (também conhecido como OWASP ZAP) para análise passiva, além de ferramentas para checar configurações web, cabeçalhos de segurança e HTTPS. A seleção das ferramentas segue em aberto.

[Referência técnica do ZAP sobre análise passiva](https://www.zaproxy.org/docs/desktop/addons/passive-scanner/)

### Diferenciais propostos

A automação reduz o esforço de triagem. A revisão humana contextualiza os achados, e o relatório traduz os riscos em ações que gestores e equipes técnicas podem usar para priorizar correções.

### Limitações

O serviço oferece um diagnóstico inicial, limitado ao escopo autorizado e ao momento da avaliação. Não substitui um pentest completo nem garante a ausência de vulnerabilidades.

### Principais riscos e validações pendentes

#### Público e autorização

Identificar os segmentos com demanda e aplicações sob sua administração, além de confirmar quem pode autorizar a avaliação.

#### Custo, prazo e disposição a pagar

Medir o tempo de atendimento, revisão e produção do relatório e verificar se o custo permite um preço compatível com o orçamento do público.

#### Valor além dos alertas

Validar se a revisão e as orientações ajudam os clientes a entender os riscos, decidir o que corrigir e agir sobre os achados.

### Relação com as outras ideias

O **CyberCheck** é um serviço pontual de diagnóstico preventivo de aplicações web. O **CyberBR** é voltado à gestão de vulnerabilidades. O **CodeShield** tem foco na análise de código.
