# Frentes de trabalho do CyberCheck

Organização para os quatro integrantes trabalharem em paralelo. Os nomes dos responsáveis ainda serão combinados pelo time. A interface da demo ficará com outro integrante, conforme definido pelo usuário.

Após organizar as frentes, o usuário retomou o trabalho na conexão GitHub e na validação do fluxo. O estado abaixo foi atualizado em 17/11/2026; cada participante deve continuar apenas nos arquivos e contratos combinados.

## Estado atual

- Há uma primeira base de API, SQLite, integração GitHub App, worker e adaptadores dos três scanners no diretório de trabalho.
- O commit que inclui este documento compartilha a base inicial para o time. Cada frente deve partir desse mesmo commit e revisar os contratos antes de alterar os módulos.
- Os 24 testes atuais passaram na verificação de 17/11/2026. Os três scanners também foram executados com exemplos controlados. A conexão e o fluxo real pelo repositório selecionado também foram verificados, com resultado parcial documentado; isso não valida o produto completo. Há um aviso de depreciação do TestClient sobre o uso de httpx, sem falha nos testes.
- Não há frontend da aplicação, login multiusuário ou coleta de sinais de descontinuação implementados.
- A GitHub App do time foi configurada e teve acesso real validado em 17/11/2026: autenticação, repositório selecionado, resolução do commit, download temporário e listagem pela API. Os testes automatizados continuam usando respostas simuladas; o fluxo pela fila e relatório também foi validado com código real, com dependências explicitamente não avaliadas por falta de arquivo suportado. Repositório privado adicional e revogação ainda precisam de validação real.
- O site em `website/` é a apresentação do projeto, não a interface operacional da demo.

## Divisão de propriedade dos arquivos

Cada arquivo deve ter uma frente responsável. As pastas futuras abaixo são sugestões de localização; não foram criadas nesta etapa.

| Frente | Responsabilidade | Arquivos de propriedade exclusiva | Branch sugerida |
| --- | --- | --- | --- |
| 1. Backend e dados | API, autenticação do CyberCheck, fila e histórico | `cybercheck/api.py`, `cybercheck/store.py`, `cybercheck/config.py`, `cybercheck/__main__.py`; novos testes em `tests/test_api.py` e `tests/test_store.py` | `feat/backend` |
| 2. Análises e executor | Rodar scanners, normalizar achados e gerenciar execução | `cybercheck/scanners.py`, `cybercheck/worker.py`, `tools.lock.json`, `scripts/install_scanners.py`; novos testes em `tests/test_scanners.py` e `tests/test_worker.py` | `feat/analyses` |
| 3. GitHub e manutenção de dependências | Acesso aos repositórios e evidências de descontinuação/arquivamento | `cybercheck/github.py`; novo `cybercheck/maintenance.py`; novos testes em `tests/test_github.py` e `tests/test_maintenance.py` | `feat/github` |
| 4. Interface da demo | Telas e interação com a API | Novos `templates/` e `static/`; ajustes em `website/` somente se necessários e combinados | `feat/demo-ui` |

## Frente 1 — Backend e dados

### Já feito

- API, Bearer token local, validação de entrada, SQLite, fila, histórico e rota de exclusão.
- Testes de autenticação, duplicatas, recuperação da fila e exclusão; fluxo real de solicitação e consulta do relatório.

### Falta fazer

- Revisar e estabilizar as rotas, os formatos JSON e os códigos de erro para o frontend.
- Completar os modelos de resposta e a documentação OpenAPI.
- Ampliar validação de concorrência e conectar histórico/exclusão à futura autorização por usuário; as operações iniciais já possuem testes.
- Definir a evolução da autenticação: o código inicial usa um token de operador único, não contas de usuários independentes.
- Garantir que a autorização acompanhe essa evolução; não apresentar a base atual como um serviço multiusuário pronto.
- Fazer os ajustes mínimos para servir os templates e arquivos estáticos entregues pela frente 4, quando necessário.

**Entrega:** API testada e contrato estável para as outras frentes, com persistência e regras de acesso claras.

**Não alterar:** scanners, download do GitHub ou implementação visual das telas.

## Frente 2 — Análises e executor

### Já feito

- Adaptadores dos três scanners, instalador com hashes, worker separado e normalização dos resultados.
- Timeout, extração defensiva, descarte temporário e representação de análises parciais.
- Três scanners executados em exemplos controlados; Bandit e Betterleaks executados também no repositório real.
- Falta de fonte de dependências identificada no fluxo real e tratada explicitamente como verificação não realizada, com testes de regressão.

### Falta fazer

- Revisar os adaptadores e fixar as configurações e versões efetivamente suportadas.
- Validar exemplos vulneráveis e corrigidos das categorias aprovadas, incluindo falsos positivos.
- Ampliar a matriz de falhas de ferramentas e rede. Já há testes de ferramenta ausente, falta de fonte de dependências, timeout e recuperação de trabalhos interrompidos.
- Ampliar os testes de descarte e proteção de evidências; o descarte e o resultado parcial já foram observados no fluxo real.
- Completar os limites de recursos e o isolamento necessário ao executor. Processo separado não equivale a isolamento de segurança.
- Integrar os sinais de manutenção produzidos pela frente 3 sem alterar seus critérios.

**Entrega:** worker executa as verificações e devolve achados e cobertura reais, sem executar o projeto analisado nem testar credenciais contra provedores.

**Não alterar:** endpoints, schema do banco, login ou telas.

## Frente 3 — GitHub e manutenção de dependências

### Já feito

- App da organização cadastrada e instalada com leitura de Contents/Metadata, somente no repositório escolhido.
- Configuração local protegida; autenticação real, listagem, resolução de SHA e download temporário validados.
- Fluxo integrado com API, fila e worker validado sem colocar credenciais ou relatórios no Git. Ver [GITHUB.md](GITHUB.md).

### Falta fazer

- Testar o acesso real a um repositório privado próprio autorizado; a instalação inicial e o acesso ao repositório selecionado já funcionam.
- Ampliar testes reais de paginação e revogação. Resolução de commit e download da revisão já foram testados com GitHub real.
- Apoiar a frente 1 no fluxo de autorização do usuário, sem editar a API ou as configurações em paralelo.
- Associar corretamente o pacote Python ao projeto de origem.
- Coletar apenas os dois sinais aprovados: aviso explícito dos mantenedores e repositório arquivado, com fonte e data.
- Verificar sucessores ou mudança de endereço e sugerir alternativas somente quando houver evidências de adequação; caso contrário, informar que não foi identificada uma alternativa.
- Combinar com a frente 2 como fornecer o inventário de dependências e como retornar essas evidências.

**Entrega:** acesso autorizado a commits e evidências verificáveis sobre manutenção, sem classificar uma biblioteca como abandonada apenas por inatividade.

**Não alterar:** schemas do SQLite, execução dos scanners ou interface.

## Frente 4 — Interface da demo

### Falta fazer

- Criar as telas de seleção de repositório, confirmação da autorização e início manual da análise.
- Mostrar andamento, falhas e verificações incompletas.
- Exibir os problemas por tipo e prioridade, sem nota ou score.
- Apresentar evidências, confiança, impacto e ação sugerida, além de commit e data/hora.
- Implementar histórico e exclusão com confirmação.
- Validar uso em desktop e celular e tratar estados vazios e erros.

**Entrega:** interface que consome a API real. Enquanto houver mocks de desenvolvimento, identificá-los como dados simulados.

**Não alterar:** Python do backend, banco, autenticação ou scanners. Solicitar à frente 1 qualquer rota, ajuste de CORS ou configuração para servir arquivos. Não colocar tokens reais, chave da GitHub App ou outros segredos no HTML/JavaScript ou no repositório.

## Contratos que precisam ser combinados antes do trabalho paralelo

### API ↔ interface

As rotas iniciais existentes são:

| Método e rota | Função |
| --- | --- |
| `GET /health` | Estado da API |
| `GET /api/repositories` | Repositórios acessíveis à instalação configurada |
| `POST /api/analyses` | Solicitar análise manual de uma referência |
| `GET /api/analyses` | Consultar histórico |
| `GET /api/analyses/{id}` | Consultar relatório e problemas agrupados |
| `DELETE /api/analyses/{id}` | Excluir análise; execução em andamento retorna conflito |

O corpo inicial da solicitação contém `repository_id`, `reference` opcional, `authorization_confirmed` e `dependency_lookup`. Esta última opção autoriza a consulta externa de metadados de dependências. As rotas de dados exigem Bearer token na base atual.

As frentes 1 e 4 devem confirmar esse contrato antes de implementar a integração visual. O login GitHub por usuário ainda não existe: não montar telas pressupondo que esse fluxo esteja pronto.

### Executor ↔ API e banco

Estados iniciais: `queued`, `running`, `completed`, `partial` e `failed`.

O relatório registra repositório, SHA, datas, achados e estado/versão de cada ferramenta. O estado `completed` significa que as verificações configuradas terminaram, não que o projeto está seguro. Regras de escopo e casos não cobertos precisam ficar explícitos.

Prioridades: `critical`, `high`, `medium`, `low` e `review`. A interface pode traduzir os rótulos, mantendo os valores do contrato. Confiança e prioridade são campos distintos.

O formato inicial de um achado está em `cybercheck/scanners.py`, na função `finding`. Alterações nos campos devem ser combinadas entre as frentes 1, 2 e 4 antes de serem aplicadas.

### Executor ↔ GitHub

Preservar ou negociar explicitamente as interfaces existentes:

- `repositories(page)`: lista os repositórios autorizados.
- `resolve(repository_id, reference)`: retorna nome completo, SHA e referência.
- `download(analysis, destination)`: baixa o arquivo da revisão registrada para o destino indicado.

A coleta de manutenção deve ficar em módulo separado do adaptador de scanners. As frentes 2 e 3 precisam acordar seu formato de entrada e saída antes de integrar essa funcionalidade.

## Arquivos compartilhados: um integrador responsável

Até o time escolher uma pessoa, considerar a frente 1 responsável pela integração destes arquivos:

- `pyproject.toml`, eventual lockfile Python, `.env.example` e `.gitignore`.
- `README.md`, planejamento em `markdown/` e este documento.
- `tests/test_backend.py` e `tests/test_security.py`, que já abrangem múltiplas frentes. As frentes devem criar seus novos testes nos arquivos exclusivos indicados na tabela, evitando editar esses dois simultaneamente.
- Workflows em `.github/` e futuras alterações de estrutura do repositório.

Quem precisar adicionar uma dependência ou variável de ambiente comunica a necessidade ao integrador, em vez de editar o arquivo compartilhado em paralelo. Não mover arquivos ou renomear funções de outra frente sem combinar.

## Ordem de integração sugerida

1. Revisar e compartilhar a base atual em um commit comum; definir os responsáveis e confirmar os contratos.
2. Cada participante cria sua branch a partir dessa base e trabalha nos arquivos da própria frente.
3. Frente 1 estabiliza a API enquanto frentes 2 e 3 validam seus módulos; frente 4 pode construir as telas com dados de exemplo identificados.
4. Integrar as mudanças em partes pequenas, atualizando a branch antes de abrir cada PR.
5. Integrador executa o conjunto de testes e verifica o fluxo GitHub → fila → análise → relatório → exclusão.

Hospedagem, provedor/modelo de IA, monitoramento contínuo, GitHub Actions para análise automática e planos comerciais não precisam ser resolvidos por essas frentes agora.
