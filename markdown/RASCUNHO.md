# Rascunho do projeto — Hack Brasil 2026

## Nome do projeto

CyberCheck

## Frase de apresentação / resumo

Ajuda desenvolvedores autônomos e pequenas equipes a encontrar problemas de segurança nos seus projetos e entender o que corrigir primeiro.

## Trilha

Cibersegurança

## Descrição do projeto

### Problema a ser resolvido

Desenvolvedores autônomos e pequenas equipes precisam cuidar da segurança dos sistemas que constroem, mesmo sem contar com especialistas dedicados. Além de encontrar possíveis falhas no código, precisam verificar bibliotecas utilizadas, credenciais expostas e configurações que podem colocar o projeto em risco.

O desafio que queremos resolver é transformar essas verificações em decisões práticas: onde está o problema, qual pode ser seu impacto, o que merece atenção primeiro e como começar a corrigir. Um alerta técnico isolado pode exigir investigação e conhecimento de segurança que o desenvolvedor ainda não possui.

Há também o risco de depender de uma biblioteca descontinuada ou cujo repositório foi arquivado. Nesses casos, atualizar a versão pode não ser suficiente: o desenvolvedor precisa avaliar possíveis substituições e entender as mudanças necessárias.

### Público-alvo

Desenvolvedores autônomos e pequenas equipes que mantêm projetos próprios ou de clientes e querem incorporar verificações de segurança ao desenvolvimento. O foco inicial será em projetos Python, sem limitar a proposta a sites ou aplicações web.

### Objetivo e solução proposta

O CyberCheck pretende reunir problemas de segurança em uma apresentação clara, agrupada por tipo e organizada por prioridade, com evidências e ações sugeridas. O objetivo é ajudar o desenvolvedor a entender os riscos identificados e tomar decisões de correção com mais autonomia.

O usuário poderá conectar o GitHub, autorizar os repositórios que deseja avaliar e iniciar uma análise. Cada problema será apresentado com sua localização, quando aplicável, possível impacto e orientação de correção. Os resultados indicarão a versão do código e a data da análise, permitindo acompanhar novas avaliações após as mudanças.

### Primeira versão

O MVP terá três frentes:

- **Código:** procurar possíveis falhas, como injeções de SQL e comandos, execução insegura de código e carregamento inseguro de dados.
- **Dependências:** identificar versões com vulnerabilidades conhecidas, avisos de descontinuação e repositórios arquivados, sugerindo atualizações ou possíveis alternativas quando necessário.
- **Segredos e configurações:** procurar credenciais expostas e configurações potencialmente inseguras.

O foco da entrega será expor os problemas e orientar ações. Cada achado terá evidências e incertezas explícitas, para distinguir uma suspeita de uma falha confirmada. A ausência de alertas não será apresentada como garantia de segurança.

### Impacto esperado

Queremos reduzir a dificuldade de interpretar alertas e decidir por onde começar, aproximando as verificações de segurança do cotidiano de quem desenvolve com uma equipe pequena. A utilidade da proposta será avaliada pela clareza dos resultados, pela pertinência das orientações e pela capacidade de apoiar correções nos projetos analisados.

### Evolução futura

Após validar o diagnóstico inicial, pretendemos avaliar o monitoramento de novos avisos de segurança e a notificação dos responsáveis por projetos potencialmente afetados. Essa etapa ficará fora da primeira versão.

### Uso responsável

A proposta tem finalidade defensiva. As análises e demonstrações serão realizadas em projetos próprios ou com autorização por escrito, sem expor dados pessoais reais de terceiros. O acesso será limitado aos repositórios autorizados pelo usuário.
