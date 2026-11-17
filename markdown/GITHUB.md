# Configuração da GitHub App

## Cadastro na organização

A App deve pertencer à organização **Hack-Brasil-2026-sudoers**. O usuário confirmou ser proprietário da organização.

[Abrir cadastro pré-preenchido](https://github.com/organizations/Hack-Brasil-2026-sudoers/settings/apps/new?name=CyberCheck%20Sudoers&url=https%3A%2F%2Fgithub.com%2FHack-Brasil-2026-sudoers%2Fhack-brasil-2026&description=Diagnostico%20defensivo%20de%20repositorios%20Python&contents=read&metadata=read&public=false&webhook_active=false&request_oauth_on_install=false).

Conferir antes de criar:

- Nome: CyberCheck Sudoers; caso já esteja em uso, escolher outro nome disponível.
- Homepage: repositório público do projeto.
- Repository permissions: **Contents: Read-only** e **Metadata: Read-only**.
- Demais permissões: sem acesso.
- Webhooks: desativados, pois as análises serão iniciadas manualmente.
- OAuth durante instalação, callback e setup URL: não configurar nesta etapa. O backend atual usa autenticação da instalação, não login individual do usuário.
- Instalação: somente na conta proprietária, para o teste inicial da organização. Acesso a outras contas é uma evolução separada.

O link é um guia para recriar a configuração, se necessário. A App do time já está cadastrada e instalada, conforme a seção de estado; não é necessário criar outra.

## Instalação e credenciais locais

Depois de criar a App:

1. Anotar o **App ID** na página de configurações. Não confundir com Client ID.
2. Gerar uma chave privada e baixar o arquivo PEM. Mantê-lo fora do repositório, em diretório privado, com permissão de leitura apenas do proprietário.
3. Em **Install App**, instalar na organização com **Only select repositories** e selecionar inicialmente apenas `hack-brasil-2026`. Adicionar outros projetos de teste somente quando necessário.
4. Obter o **Installation ID** no endereço da página de configuração dessa instalação.
5. Preencher no `.env` local: `GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID` e `GITHUB_PRIVATE_KEY_PATH` com o caminho absoluto do PEM.

Não enviar a chave ou tokens pelo chat, colocá-los no frontend ou adicioná-los ao Git. O `.env` é ignorado e contém a configuração local validada. Em uma nova máquina, ele deve ser preenchido localmente; o repositório não distribui essas credenciais.

## Verificação após configurar

Com a virtualenv instalada:

```bash
.venv/bin/python -m cybercheck api
```

Em `http://127.0.0.1:8000/docs`, usar **Authorize** com o token local e chamar `GET /api/repositories`. A resposta deve listar somente os repositórios autorizados à instalação.

Em seguida, validar resolução do commit, download e análise de um projeto próprio. O worker é iniciado separadamente:

```bash
.venv/bin/python -m cybercheck worker
```

O login individual e o isolamento multiusuário ainda não estão implementados. Não publicar esse backend de operador único como serviço aberto.

## Estado

A App `cybercheck-sudoers` está criada e instalada na organização, com Contents e Metadata somente leitura e seleção explícita de repositórios. Os IDs e o caminho da chave RSA estão configurados no `.env` local; a chave está com permissão 600 e não foi copiada ao Git.

Verificação real em 17/11/2026:

- Autenticação da App e emissão do token da instalação: OK.
- Listagem: um repositório autorizado, `Hack-Brasil-2026-sudoers/hack-brasil-2026`.
- Resolução da branch padrão `main` para o commit `35bb2ff6d80982a08ee32d59e12de12d4df1cb79`: OK.
- Download e extração temporária da revisão: OK; arquivos descartados após a verificação.
- Rota `GET /api/repositories` com acesso real ao GitHub: OK; requisição sem token local bloqueada com 401.

Depois da configuração, o fluxo completo também foi validado na branch `pedro`, commit `156862f5d413c74bd2888f4e45c594883511cc88`: solicitação autenticada pela API, fila SQLite, worker, download, scanners, consulta do relatório e descarte dos arquivos temporários.

Bandit e Betterleaks concluíram. O OSV-Scanner não encontrou arquivo de dependências suportado nessa revisão, então o relatório registra a verificação como não realizada (`skipped`) e a análise como parcial. Isso não significa ausência de vulnerabilidades nas dependências. A análise de verificação ficou no histórico local em `.data/`, fora do Git.

Foi adicionado tratamento específico para esse caso e a suíte passou com 24 testes. Login individual, acesso a outro repositório privado e revogação da instalação ainda precisam de testes próprios.

Referências: [cadastro de GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app) e [parâmetros de pré-preenchimento](https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-using-url-parameters).
