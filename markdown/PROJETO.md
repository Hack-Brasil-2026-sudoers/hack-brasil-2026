# CyberCheck

Documento vivo da proposta. Atualizado em 15/11/2026 com as decisões da conversa.

## Proposta

O CyberCheck ajuda desenvolvedores autônomos e pequenas equipes a identificar possíveis problemas de segurança nos seus projetos e entender o que corrigir primeiro.

A primeira versão terá foco na análise interna de repositórios. A entrega reúne achados, evidências, localização, possível impacto e ações de correção priorizadas.

O produto pode atender diferentes tipos de software, sem ficar restrito a aplicações web. A cobertura efetiva depende das linguagens, ferramentas e verificações implementadas.

## Decisões tomadas

- Público inicial: desenvolvedores autônomos e pequenas equipes.
- Modalidade inicial: análise interna do repositório.
- Primeira linguagem analisada no MVP: Python.
- Entrada inicial dos projetos: integração com GitHub.
- Integração via GitHub App, atendendo repositórios públicos e privados, com acesso de leitura limitado aos repositórios escolhidos pelo usuário.
- Código obtido em cópia temporária para análise e apagado ao terminar; guardar o relatório com evidências necessárias e segredos mascarados.
- Cada análise deve registrar o repositório, o SHA completo do commit efetivamente analisado e a data/hora da análise, exibidos no relatório.
- Disparo no MVP: manual, com o usuário selecionando o repositório e acionando “Iniciar análise”. Para o futuro, fica aberta a integração com GitHub Actions ou outros mecanismos de automação, como eventos do GitHub, pipelines de CI/CD ou agendamentos. Nenhum mecanismo futuro está escolhido ou incluído no MVP.
- Foco: problemas de segurança com ações sugeridas.
- Frentes confirmadas do MVP: código, dependências e segredos/configurações.
- Análise externa de sites e APIs: modalidade independente, prevista como evolução.
- Monitoramento de novos riscos: evolução futura.
- Planos comerciais e cobrança: decidir posteriormente.

## Frentes de análise confirmadas para o MVP

O MVP terá as três frentes abaixo. As regras e verificações específicas ainda serão escolhidas; a aprovação das frentes não implica cobertura completa de cada categoria.

| Categoria | Exemplos |
| --- | --- |
| Código potencialmente vulnerável | SQL injection, injeção de comandos de shell e outros padrões inseguros |
| Dependências | Versões afetadas por vulnerabilidades conhecidas |
| Segredos e configurações | Possíveis senhas, tokens e chaves expostos; configurações inseguras presentes no repositório |

Cada achado deve distinguir observação, suspeita e problema confirmado. A ausência de alertas não garante segurança. A presença de uma URL como `/admin`, isoladamente, não comprova vulnerabilidade.

### Cobertura inicial de código Python confirmada

- Possíveis SQL injections.
- Possíveis injeções de comandos de shell.
- Uso perigoso de `eval` e `exec` com dados externos.
- Desserialização insegura de dados não confiáveis.

As verificações devem considerar a origem dos dados e o contexto de uso. A simples presença de uma função não confirma uma vulnerabilidade. A ferramenta inicial é Bandit; regras específicas e limites de detecção ainda serão validados.

### Cobertura inicial de dependências confirmada

- Identificar bibliotecas e versões utilizadas, indicando onde foram encontradas.
- Consultar vulnerabilidades conhecidas e apresentar o problema, a gravidade e a versão corrigida, quando disponível.
- Avaliar sinais de abandono ou descontinuação da dependência.
- Sugerir possíveis substituições quando houver abandono, descontinuação ou ausência de uma correção viável.

Uma versão afetada não comprova que a falha é explorável naquele projeto. Da mesma forma, tempo sem releases ou commits, isoladamente, não comprova abandono: uma biblioteca pode estar estável.

No MVP, a avaliação de manutenção fica limitada a dois sinais: aviso explícito dos mantenedores sobre abandono/descontinuação ou repositório de origem arquivado. Registrar fonte, data da consulta e evidência. Não usar tempo sem commits/releases, frequência de atividade ou ausência de resposta como critérios nesta etapa. Apresentar o fato observado: um repositório arquivado pode ter um sucessor ou mudança de endereço, portanto não afirmar abandono definitivo sem contexto. A ausência desses sinais não comprova manutenção ativa. Os mecanismos de coleta e os critérios de escolha de alternativas ainda serão definidos.

As alternativas devem ser verificadas quanto à manutenção, adequação ao uso no projeto, licença e esforço de migração. Explicar por que cada candidata pode servir, diferenças relevantes e incertezas. Não prometer substituição automática ou compatibilidade direta; quando não houver alternativa adequada identificada, informar isso.

### Cobertura inicial de segredos e configurações confirmada

- Possíveis credenciais expostas no repositório, como senhas, tokens e chaves.
- Modo de depuração habilitado em configurações potencialmente destinadas à produção.
- Validação de certificados TLS desativada.

Considerar o contexto: exemplos fictícios, configurações de desenvolvimento e testes não devem ser tratados automaticamente como exposição real em produção. Apresentar evidências e incertezas, mascarar segredos nos resultados e não testar credenciais contra serviços externos. Regras específicas e frameworks cobertos ainda serão definidos.

## Experiência proposta

1. O desenvolvedor autoriza a GitHub App nos repositórios escolhidos e seleciona um deles para análise. O MVP atenderá repositórios públicos e privados, com as permissões de leitura necessárias. As permissões exatas e o fluxo de autenticação serão verificados na documentação do GitHub antes da implementação.
2. O desenvolvedor aciona “Iniciar análise”; o sistema identifica as tecnologias e executa as verificações disponíveis.
3. O resultado apresenta os achados com evidências e ações sugeridas.
4. O desenvolvedor corrige e pode realizar uma nova análise para comparar os resultados.

Esse fluxo orienta o produto; os detalhes de implementação ainda estão em definição.

### Histórico das análises

Os resultados devem ficar vinculados à revisão exata do código: repositório, SHA completo do commit e data/hora da análise. O relatório representa essa revisão naquele momento, sem presumir que descreve o estado atual do projeto. Registrar o horário com fuso explícito.

A cópia do código é temporária e deve ser descartada ao encerrar a execução, inclusive em caso de falha. O relatório pode conter os trechos necessários como evidência, com segredos mascarados. Os relatórios e seus metadados permanecem no histórico até o usuário excluí-los. O usuário deve poder excluir os próprios relatórios e suas evidências associadas. O fluxo concreto de exclusão ainda será definido.

## Ferramentas escolhidas para o MVP

- **Bandit (Apache-2.0):** padrões inseguros no código Python e algumas configurações.
- **OSV-Scanner (Apache-2.0):** vulnerabilidades conhecidas nas dependências identificadas em arquivos suportados, preferindo versões resolvidas.
- **Betterleaks (MIT):** possíveis credenciais e segredos expostos.

Seleção confirmada pelo usuário. Versões, regras, configuração e cobertura prática ainda serão validadas. A avaliação de abandono no MVP usará avisos explícitos dos mantenedores e arquivamento do repositório de origem. A coleta dessas evidências e a sugestão de substituições ainda exigem definição técnica. OpenSSF Scorecard não é necessário para esses dois sinais e permanece uma referência para possível evolução, sem adoção confirmada.

## Apresentação dos resultados

Expor os problemas encontrados, agrupados por tipo e organizados por prioridade. Não atribuir nota geral, pontuação por categoria ou score de segurança ao projeto.

Cada achado apresenta evidência, localização quando aplicável, possível impacto e ação sugerida, vinculado ao commit e à data/hora da análise. Distinguir confiança de prioridade: uma suspeita de alto impacto continua sendo uma suspeita.

As prioridades serão crítica, alta, média e baixa, considerando a gravidade indicada pela ferramenta e o contexto disponível, sempre com justificativa por achado. Quando faltar informação para classificar, apresentar “prioridade a revisar”. A confiança permanece separada da prioridade. Os nomes finais das categorias e as regras detalhadas de classificação ainda serão definidos. A referência ao Scorecard inspira a organização das verificações, não uma pontuação.

## Stack confirmada para o MVP

- Backend em Python com FastAPI.
- Interface em HTML/CSS e templates Jinja2, com pouco JavaScript.
- SQLite para persistir usuários, projetos, análises e achados.
- Processo separado em Python para executar Bandit, OSV-Scanner e Betterleaks sem bloquear o atendimento do site.

A prioridade é implementar o programa. Hospedagem e formato de disponibilização da demo serão decididos depois; não há compromisso com demo local, AWS ou outro provedor. Isolamento do executor e mecanismo de coordenação das análises precisam ser tratados na implementação. Um processo separado não constitui, por si só, isolamento de segurança. O SQLite exige armazenamento persistente no ambiente escolhido.

Antes da submissão, definir a disponibilização da demo conforme os itens 7.2 e 7.3 do regulamento. Essa decisão fica para depois da implementação e não define o ambiente de desenvolvimento.

## Papel da IA no MVP

Ferramentas especializadas geram os achados; a IA ajuda a explicá-los, contextualizá-los e sugerir correções com base nas evidências. A IA não será a única responsável pela detecção nem confirmará automaticamente vulnerabilidades.

Enviar à IA o achado estruturado e apenas o trecho mínimo de código necessário, com segredos mascarados, em vez do repositório inteiro. O conteúdo extraído do projeto continua sendo dado não confiável, mesmo em formato estruturado.

A IA produzirá explicações e sugestões, sem acesso ao GitHub nem permissão para executar comandos ou alterar arquivos. As sugestões devem permanecer vinculadas às evidências e indicar incertezas.

Decisão do usuário: manter provedor e modelo de IA em aberto neste momento, inclusive enquanto os benefícios do hackathon são avaliados. Essa escolha não deve bloquear a implementação das análises e da apresentação das evidências. Até configurar e autorizar a integração, não enviar dados para IA externa nem apresentar explicações como geradas por IA. Custos e tratamento dos dados ainda serão definidos. Antes de usar um serviço externo, informar ao usuário quais dados serão enviados e definir a autorização correspondente; a integração com GitHub não autoriza esse compartilhamento por si só.

## Evolução: monitoramento

Acompanhar novos avisos de segurança, cruzá-los com o inventário dos projetos e reavaliar possíveis exposições. Notificar os responsáveis com evidências, urgência e orientação de correção, deixando explícito quando a exposição ainda não foi confirmada.

Fontes, periodicidade, canais de contato e planos comerciais permanecem em aberto.

## Pesquisa para escolher as linguagens

Consulta realizada em 15/11/2026. A prioridade é escolher linguagens relevantes para o público, sem confundir a linguagem analisada com a linguagem usada para construir o CyberCheck.

### Uso declarado por desenvolvedores

O Stack Overflow Developer Survey 2026 apresenta os seguintes resultados na pergunta de linguagens, com 14.099 respondentes:

| Linguagem | Uso declarado |
| --- | ---: |
| JavaScript | 62,0% |
| Python | 58,0% |
| TypeScript | 43,8% |
| Java | 27,6% |
| C# | 27,1% |
| C++ | 24,3% |
| C | 21,8% |
| PHP | 17,7% |
| Go | 16,5% |

A pergunta permite múltiplas respostas: os percentuais não são fatias exclusivas de mercado e não devem ser somados. A tabela seleciona linguagens candidatas; não reproduz o ranking completo, que também inclui SQL, HTML/CSS e shells.

Fonte: [Stack Exchange Inc., Stack Overflow Developer Survey 2026 — linguagens](https://survey.stackoverflow.co/2026/technology/data/languages), dados sob ODbL 1.0. A [metodologia](https://survey.stackoverflow.co/2026/methodology) descreve o recrutamento pela comunidade e canais do Stack Overflow; a amostra não representa automaticamente todos os desenvolvedores.

### Atividade no GitHub

O Octoverse 2026 informa que TypeScript, Python e JavaScript tiveram os maiores aumentos de contribuidores mensais entre as dez principais linguagens, de setembro de 2025 a setembro de 2026. Também registra que TypeScript havia assumido a liderança por contribuidores em 2025.

A métrica atribui contribuidores à linguagem principal do repositório e inclui diferentes formas de participação. Ela não mede diretamente quantidade de projetos pequenos, clientes potenciais ou demanda por análise de segurança.

Fonte: [GitHub Octoverse 2026](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/).

### Interpretação e decisão

Não foi identificado, nesta pesquisa, um ranking diretamente comparável de linguagens usadas especificamente em pequenos projetos de desenvolvedores autônomos ou pequenas equipes brasileiras. As duas fontes acima são indicadores gerais, não uma medição desse público.

**Decisão confirmada pelo usuário:** começar pela análise de projetos Python no MVP. JavaScript/TypeScript são candidatos a expansão futura, ainda sem compromisso de implementação. A escolha de começar por Python é uma decisão de escopo apoiada pelos indicadores gerais, não uma conclusão estatística de que Python lidera entre pequenos projetos.

C e C++ continuam sendo opções, especialmente pela experiência do proponente. Os dados gerais não justificam escolhê-las como prioridade de alcance por si só; familiaridade da equipe, ferramentas disponíveis e qualidade da análise também devem pesar.

Antes de prometer suporte, avaliar a cobertura real das ferramentas para cada linguagem e validar as tecnologias usadas por potenciais usuários.

## Próximas decisões, uma por vez

1. Priorizar a implementação do programa, tratando execução e isolamento das análises; decidir hospedagem e disponibilização da demo posteriormente.
2. Definir as versões de Python e os frameworks cobertos.
3. Detalhar regras e critérios das três frentes de análise confirmadas.
4. Retomar provedor/modelo de IA e tratamento dos dados enviados posteriormente; decisão adiada, sem bloquear a implementação.
5. Definir critérios de demonstração e fluxo de exclusão dos relatórios; retenção até exclusão pelo usuário está confirmada.

## Relação com os arquivos existentes

[CyberCheck-Hack-Brasil.md](CyberCheck-Hack-Brasil.md) preserva a conversão do PDF original, cuja proposta era focada em pequenos negócios e segurança web. Este documento registra a proposta atual discutida, que evoluiu para pequenos desenvolvedores e análise interna de repositórios.
