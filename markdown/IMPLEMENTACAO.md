# Guia de implementação do CyberCheck

Estado em 17/11/2026: backend inicial implementado e conexão real da GitHub App validada, incluindo execução pela fila e consulta do relatório. O trabalho foi retomado pelo usuário na conexão GitHub e na validação do fluxo, mantendo a separação das frentes. A divisão de responsabilidades e dos arquivos está em [FRENTES-DE-TRABALHO.md](FRENTES-DE-TRABALHO.md). A interface da demo ficará com outro integrante. Este arquivo orienta o trabalho técnico; a explicação do produto e a pesquisa estão em [PROJETO.md](PROJETO.md).

## Como conduzir o trabalho

- Decidir um assunto por vez com o usuário.
- Distinguir decisão confirmada, recomendação e questão pendente.
- Não converter recomendações em requisitos aprovados.
- Atualizar estes dois documentos conforme as decisões forem tomadas.
- Preservar a transcrição do PDF como referência histórica.
- Não iniciar a implementação só porque há um fluxo proposto neste documento.

## Implementado e validado

- API com Bearer token de operador único, validação de entrada, histórico e exclusão; testes de acesso sem token e conflitos.
- SQLite com fila persistente, prevenção de duplicatas ativas, limite de fila e recuperação de execuções interrompidas.
- Worker separado, download limitado ao commit, extração com rejeição de caminhos inseguros e links, timeout e descarte de temporários.
- Adaptadores Bandit 1.9.4, OSV-Scanner 2.7.1 e Betterleaks 1.10.1; versões e hashes dos binários em `tools.lock.json`.
- Achados agrupáveis por tipo/prioridade, evidências estruturadas e confiança separada, sem código/matches ou segredos brutos nos resultados normalizados.
- GitHub App da organização configurada localmente: Contents e Metadata somente leitura, instalação em repositório selecionado. Autenticação, listagem, commit e download testados com GitHub real.
- Fluxo real API → fila → worker → scanners → relatório validado em revisão da branch `pedro`; dependências ficaram não avaliadas por ausência de arquivo suportado, preservando o estado parcial.
- Tratamento específico do OSV para ausência de fontes de pacotes (`skipped`), sem mascarar outros erros como falta de cobertura.
- 24 testes automatizados passaram. Scanners também testados com exemplos controlados. O TestClient emite um aviso não bloqueante de depreciação do httpx.

Credenciais e resultados locais ficam em `.env`/`.data`, ignorados pelo Git. A chave privada está fora do repositório; `.env` e chave têm permissão 600. Verificação pré-push por valores locais, padrões e Betterleaks não detectou segredos nos arquivos versionáveis nem no histórico Git local.

## Requisitos confirmados

- Atender desenvolvedores autônomos e pequenas equipes.
- Começar pela análise interna de repositórios.
- Analisar projetos Python na primeira versão.
- Apresentar problemas agrupados por tipo e organizados por prioridade, sem nota geral, pontuação por categoria ou score de segurança. Distinguir confiança de prioridade. Usar crítica, alta, média e baixa, considerando gravidade indicada pela ferramenta e contexto disponível, com justificativa por achado. Sem informação suficiente, apresentar “prioridade a revisar”. Regras detalhadas de classificação ainda serão definidas.
- Ferramentas escolhidas: Bandit (Apache-2.0), OSV-Scanner (Apache-2.0) e Betterleaks (MIT); validar versões, regras e cobertura.
- Fornecer os repositórios por integração com GitHub desde o MVP.
- Usar GitHub App para repositórios públicos e privados, com permissões de leitura necessárias e acesso limitado aos repositórios escolhidos pelo usuário.
- Manter o código em cópia temporária durante a análise e descartá-lo ao encerrar a execução, inclusive em falhas; guardar o relatório com evidências necessárias e segredos mascarados.
- Manter relatórios e metadados no histórico até exclusão pelo usuário. Permitir que cada usuário exclua seus próprios relatórios, incluindo evidências associadas, com verificação de autorização.
- Registrar e exibir em cada análise o repositório, SHA completo do commit efetivamente analisado e data/hora com fuso explícito. O resultado deve se referir àquela revisão, não ao estado atual presumido do repositório.
- Iniciar análises manualmente no MVP: o usuário seleciona o repositório e aciona “Iniciar análise”. Manter em aberto, para evolução futura, a integração com GitHub Actions ou outras automações, como eventos do GitHub, pipelines de CI/CD ou agendamentos. Não implementar nem escolher um mecanismo automático agora.
- Procurar problemas de segurança e sugerir ações priorizadas.
- Incluir três frentes no MVP: código potencialmente vulnerável, dependências com vulnerabilidades conhecidas e segredos/configurações inseguras.
- Cobertura inicial de código Python: possíveis SQL injections, injeções de comandos de shell, uso perigoso de `eval`/`exec` com dados externos e desserialização insegura de dados não confiáveis.
- Dependências: identificar bibliotecas e versões, vulnerabilidades conhecidas e versões corrigidas, avaliar abandono/descontinuação e sugerir possíveis alternativas quando necessário.
- No MVP, limitar os sinais de abandono/descontinuação a avisos explícitos dos mantenedores e arquivamento do repositório de origem. Não usar inatividade como critério. Registrar o fato observado e possíveis sucessores; ausência de sinal não confirma manutenção ativa.
- Segredos/configurações: possíveis credenciais expostas, modo de depuração habilitado e validação de certificados TLS desativada.
- Manter a visão de produto aberta a diferentes tipos de software.
- Tratar análise externa como outra modalidade futura.
- Deixar monitoramento e planos comerciais para etapas posteriores.

## Linguagem analisada: decisão confirmada

O usuário confirmou Python como primeira linguagem analisada no MVP. JavaScript/TypeScript permanecem candidatos a expansão futura, sem implementação aprovada.

Consultar os dados e as limitações em PROJETO.md. Não afirmar que esse conjunto é comprovadamente o mais usado por pequenos desenvolvedores brasileiros.

A experiência do usuário é principalmente em C e C++. Considerá-la ao avaliar esforço e manutenção. A implementação do CyberCheck será em Python, com FastAPI no backend; essa escolha foi confirmada separadamente da linguagem analisada.

## Stack confirmada

- Python + FastAPI no backend.
- HTML/CSS + Jinja2 na interface, com pouco JavaScript.
- SQLite para usuários, projetos, análises e resultados.
- Executor em processo Python separado, rodando as três ferramentas sem bloquear as requisições do site.

Prioridade confirmada: implementar o programa primeiro. Decisão atualizada em 17/11/2026: a demo será executada localmente. Não provisionar hospedagem pública nem assumir AWS como destino nesta etapa. Execução local não significa funcionamento offline: manter as integrações GitHub e consultas de vulnerabilidades previstas. Na implementação, tratar armazenamento persistente para SQLite, isolamento do executor, limites de recursos e coordenação durável das análises. Separar processos não equivale a isolar código não confiável. Evitar iniciar análises longas apenas como tarefas em memória do processo web; o mecanismo concreto ainda será escolhido.

Antes da submissão, retomar a disponibilização da demo conforme os itens 7.2 e 7.3 do regulamento. Não condicionar o início da implementação à escolha de hospedagem e não criar recursos de nuvem nesta etapa.

## Papel da IA confirmado

- Ferramentas especializadas geram os achados; a IA explica, contextualiza e sugere correções a partir das evidências.
- Fornecer à IA o achado estruturado e somente o trecho mínimo necessário, com segredos mascarados; não enviar o repositório inteiro.
- Tratar trechos e demais campos derivados do repositório como dados não confiáveis, inclusive quando encapsulados em JSON. Validar a saída e manter a distinção entre evidência, inferência e sugestão.
- Não conceder à IA acesso ao GitHub, execução de comandos ou alteração de arquivos.
- Não usar a IA como única fonte de detecção nem promover sua interpretação a vulnerabilidade confirmada sem evidências.
- O usuário decidiu adiar a escolha de provedor/modelo de IA. Não bloquear a implementação dos scanners e dos relatórios por essa escolha. Até configurar e autorizar a integração, não enviar dados a IA externa nem rotular orientações de regras/ferramentas como geradas por IA. Tratamento dos dados e informação ao usuário devem ser definidos antes da ativação.

## Questões técnicas ainda abertas

### Referência do regulamento

Consultado o regulamento oficial em 15/11/2026, com atualização declarada de 09/11/2026. Ver [comparação com a cópia anterior](REGULAMENTO-COMPARACAO.md) e [texto atual](regulamento-atual.md).

Tecnologias são livres (6.3), IA é permitida e recomendada (6.4), e componentes de terceiros exigem respeito às licenças (6.5). Não presumir obrigação de usar patrocinadores. Manter finalidade defensiva e testes em sistemas próprios ou autorizados por escrito (5.2 e 6.9). Observar regras de repositório novo, código anterior, publicidade e congelamento de código (6.1, 6.2, 6.7 e 8.4).

### Decisões pendentes

- Validar a matriz de versões de Python: pacote declara 3.11+, mas os testes atuais rodaram em Python 3.14.10 no Linux.
- Verificações e regras concretas dentro das três frentes confirmadas; não presumir cobertura completa dos exemplos discutidos.
- Mecanismos de coleta de avisos dos mantenedores e status de arquivamento, associação correta entre pacote e repositório de origem, e critérios para selecionar alternativas.
- Ampliar validação das regras, dos formatos de dependências e dos falsos positivos; manter avisos de licença e revisar limites de uso. Versões iniciais e hashes dos binários já estão registrados.
- Login/autorização individual para além do operador local, testes reais em repositório privado, revogação e paginação. A instalação inicial da organização já foi configurada e testada.
- Interface e eventual exportação; a persistência inicial dos resultados em SQLite já existe.
- Revisão humana e regras detalhadas de classificação/mapeamento das prioridades aprovadas.
- Decisão adiada: provedor/modelo de IA, custos, retenção pelo provedor e fluxo de autorização para envio dos dados mínimos; não é pré-requisito para implementar análises e relatórios.
- Integrar a exclusão à interface e à futura autorização por usuário; a rota de exclusão já existe e foi testada no modo de operador único.

## Critérios propostos para a implementação

Detalhar e validar estes critérios quando o escopo técnico for escolhido:

- Reutilizar analisadores existentes quando cobrirem o problema; verificar a documentação e a licença antes de adotá-los.
- Registrar repositório/revisão analisados, ferramentas, versões, regras, data e cobertura da análise.
- Para cada achado, registrar categoria, localização quando aplicável, evidência, gravidade, confiança, justificativa da prioridade e ação sugerida.
- Não equiparar uma correspondência de padrão a uma vulnerabilidade explorável confirmada.
- Não afirmar que uma dependência é explorável apenas por ter versão afetada; distinguir versão afetada de exposição confirmada.
- Não concluir abandono apenas pela idade do último release ou commit. Registrar evidências, fontes, data e incerteza; distinguir descontinuação confirmada de sinais de abandono.
- Ao sugerir alternativas, verificar manutenção, adequação ao uso, licença e esforço de migração. Explicar diferenças e limites; não inventar substituições nem presumir compatibilidade direta.
- Informar erros, análises incompletas e tecnologias não cobertas.
- Tratar o conteúdo do repositório como entrada não confiável. A análise inicial não deve executar código, builds ou scripts do projeto; qualquer execução futura exige isolamento e escopo próprios.
- Limitar o acesso ao necessário e não incluir credenciais completas nos resultados.
- Nas verificações de configurações, distinguir desenvolvimento/testes de possível uso em produção e explicitar a incerteza. Não validar credenciais encontradas por meio de chamadas a serviços externos.
- Não enviar código a serviços externos sem definir esse tratamento com o usuário.

## Validação proposta para a demonstração

Após escolher linguagem e verificações, preparar exemplos controlados com versões vulneráveis e corrigidas. Verificar se os achados apontam evidências reais, se as sugestões correspondem ao problema e se os casos corrigidos deixam de produzir o mesmo alerta.

Mostrar explicitamente o que foi analisado e quais limites permaneceram. Não prometer detecção de todas as vulnerabilidades.

## Pesquisa de ferramentas e seleção

### Ferramentas candidatas pesquisadas em 15/11/2026

Seleção confirmada pelo usuário: Bandit, OSV-Scanner e Betterleaks. As demais ferramentas pesquisadas permanecem alternativas ou fontes candidatas, sem adoção confirmada. A pesquisa original antecedeu a implementação. As três ferramentas escolhidas já foram instaladas localmente e executadas; consultar a seção de estado para as versões e a cobertura validadas.

| Frente | Candidata e licença declarada | Adequação e limites |
| --- | --- | --- |
| Código e algumas configurações Python | [Bandit](https://github.com/PyCQA/bandit), Apache-2.0 | Regras para padrões inseguros; inclui exec, SQL suspeito, shell, Flask debug e validação TLS desativada. Eval e pickle constam das listas de chamadas. Não confirma origem externa dos dados nem explorabilidade por si só |
| Dependências | [OSV-Scanner](https://github.com/google/osv-scanner), Apache-2.0 | Consulta vulnerabilidades a partir de artefatos suportados. Preferir leitura de lockfiles com versões resolvidas, sem instalar ou executar o projeto |
| Segredos | [Betterleaks](https://github.com/betterleaks/betterleaks), MIT; [Gitleaks](https://github.com/gitleaks/gitleaks), MIT, como alternativa | Avaliar modo de varredura estática, mascaramento e saída estruturada. Gitleaks declara que novos releases serão apenas correções de segurança e direciona novos recursos ao Betterleaks. Isso não equivale a abandono |
| Sinais de manutenção | [OpenSSF Scorecard](https://github.com/ossf/scorecard), Apache-2.0 | Avaliar sinais da verificação Maintained no repositório de origem da dependência. Não usar score ou inatividade isolados como confirmação de abandono; não fornece automaticamente uma substituição adequada |

Fontes de cobertura: [plugins Bandit](https://bandit.readthedocs.io/en/latest/plugins/index.html), [chamadas perigosas](https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html), [SQL B608](https://bandit.readthedocs.io/en/latest/plugins/b608_hardcoded_sql_expressions.html), [artefatos e manifests OSV-Scanner](https://google.github.io/osv-scanner/supported-languages-and-lockfiles/), [verificações Scorecard](https://github.com/ossf/scorecard/blob/main/docs/checks.md).

OSV-Scanner documenta suporte a arquivos Python como requirements.txt, poetry.lock e uv.lock, entre outros. Versões extraídas de manifests podem não refletir o ambiente implantado; sem versões resolvidas, indicar a limitação. A consulta externa de vulnerabilidades também exige registrar quais metadados de dependências saem do ambiente.

[pip-audit](https://github.com/pypa/pip-audit), Apache-2.0, é outra candidata para dependências Python. Sua própria documentação alerta que a resolução pode envolver operações equivalentes à instalação: não adotar a execução genérica sobre requirements não confiáveis como se fosse análise estritamente estática. Avaliar modo/configuração compatíveis com nossas restrições antes de considerar seu uso.

[Semgrep CE](https://semgrep.dev/products/community-edition/) tem motor aberto LGPL-2.1, mas as regras devem ser avaliadas separadamente. A [Semgrep Rules License](https://semgrep.dev/legal/rules-license/) limita o uso das regras cobertas a fins internos e não permite disponibilizá-las como serviço. Não adotar automaticamente os pacotes distribuídos sob essa licença no CyberCheck. Regras próprias ou com outra licença exigem análise individual.

Combinação aprovada: Bandit + OSV-Scanner + Betterleaks. Scorecard fica como referência para evolução, sem adoção no MVP; os dois sinais confirmados não exigem seu uso. Sugerir alternativas a dependências continuará exigindo pesquisa e validação próprias. Validar falsos positivos, exemplos corrigidos, configurações seguras e licenças das versões escolhidas antes da entrega.

## Próximo passo

Seguir a divisão de [FRENTES-DE-TRABALHO.md](FRENTES-DE-TRABALHO.md). Na frente 3, validar repositório privado/revogação e implementar os sinais de manutenção aprovados; na frente 2, completar validação de cobertura e isolamento. Frente 1 deve estabilizar os schemas da API e definir login/autorização individual com a frente 3. A frente 4 constrói a interface consumindo o contrato combinado.

A escolha de provedor/modelo de IA e de hospedagem não bloqueia esse trabalho. Não ativar IA externa nem publicar o backend de operador único como serviço aberto.
