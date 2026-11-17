# hack-brasil-2026

CyberCheck, projeto da equipe Sudoers para o Hack Brasil 2026.

## Documentação

- [Apresentação para o rascunho](markdown/RASCUNHO.md)
- [Proposta e decisões do projeto](markdown/PROJETO.md)
- [Guia de implementação](markdown/IMPLEMENTACAO.md)
- [Próximos passos](markdown/PROXIMOS-PASSOS.md)
- [Frentes de trabalho e divisão de arquivos](markdown/FRENTES-DE-TRABALHO.md)
- [Configuração da GitHub App](markdown/GITHUB.md)
- [Regulamento atual](markdown/regulamento-atual.md)
- [Comparação das versões do regulamento](markdown/REGULAMENTO-COMPARACAO.md)

O site de apresentação está em [website/](website/).

## Executar o backend

Requer Python 3.11+ e Linux nesta primeira versão do worker.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/install_scanners.py
```

Prepare um `.env` a partir de `.env.example`, gere um token aleatório para a API e siga o [guia da GitHub App](markdown/GITHUB.md). O instalador dos scanners suporta Linux x86_64 e verifica os hashes dos binários.

Inicie a API e o worker em terminais separados, na raiz do projeto:

```bash
.venv/bin/python -m cybercheck api
```

```bash
.venv/bin/python -m cybercheck worker
```

A documentação interativa fica em `http://127.0.0.1:8000/docs`. Use **Authorize** com o token local, liste os repositórios e solicite a análise com o ID retornado. A consulta externa de dependências precisa ser autorizada no campo `dependency_lookup`.

```bash
.venv/bin/python -m pytest -q
```

Esta base usa um token de operador único e ainda não oferece isolamento multiusuário. Não exponha o backend como serviço público. Resultados parciais indicam verificações sem cobertura ou com falha; ausência de alertas não garante segurança. A interface operacional da demo será feita por outro integrante.
