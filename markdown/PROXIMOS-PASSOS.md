# Próximos passos do CyberCheck

Estado atualizado em 17/11/2026. A base inicial já existe e o fluxo com GitHub real foi validado. O MVP completo ainda não está pronto. Hospedagem pública e provedor/modelo de IA continuam adiados; a interface da demo será feita por outro integrante.

## Resumo por frente

| Frente | Já feito | Falta fazer |
| --- | --- | --- |
| 1. Backend e dados | API FastAPI, Bearer token local, SQLite, fila, histórico e exclusão | Estabilizar schemas para o frontend, ampliar validação de concorrência e implementar autorização por usuário |
| 2. Análises e executor | Adaptadores dos três scanners, worker, normalização, limites iniciais e limpeza temporária | Ampliar cobertura e formatos de dependências, calibrar falsos positivos e completar isolamento/limites de recursos |
| 3. GitHub e manutenção | App da organização instalada com leitura, repositório selecionado, commit e download reais validados | Testar repositório privado/revogação, coletar sinais de descontinuação/arquivamento e avaliar alternativas |
| 4. Interface da demo | Site de apresentação existente; interface operacional ainda não iniciada | Criar telas e integrar com a API real, incluindo estados parciais, histórico e exclusão |

A propriedade dos arquivos e os contratos estão em [FRENTES-DE-TRABALHO.md](FRENTES-DE-TRABALHO.md). Cada participante deve trabalhar na sua frente; alterações em arquivos compartilhados passam pelo integrador.

## Evidências do que já foi validado

- 24 testes automatizados passaram: autenticação, validação, fila, recuperação, exclusão, extração de arquivos, normalização, timeout, proteção do ambiente e checksums.
- Bandit 1.9.4, OSV-Scanner 2.7.1 e Betterleaks 1.10.1 foram executados com exemplos controlados.
- A GitHub App real foi instalada na organização com Contents/Metadata somente leitura e seleção explícita de repositório.
- O fluxo API → fila → worker → GitHub → scanners → relatório foi executado na branch `pedro`, commit `156862f5d413c74bd2888f4e45c594883511cc88`.
- Bandit e Betterleaks concluíram nessa revisão. O OSV não encontrou fonte de dependências suportada; o relatório indica que elas não foram avaliadas e mantém o resultado parcial.
- Commit e datas ficaram registrados e os arquivos temporários foram descartados. O histórico de teste está em `.data/`, fora do Git.
- A verificação pré-push não detectou segredos nos arquivos versionáveis ou no histórico Git local. `.env` e chave privada têm permissão 600 e não estão rastreados.

Esses testes não garantem ausência de vulnerabilidades nem validam todas as versões, ambientes ou formas de entrada.

## Frente 1 — Próximas tarefas

- [ ] Definir schemas de resposta e erros estáveis, combinados com a frente 4.
- [ ] Completar a documentação OpenAPI e exemplos de integração.
- [ ] Ampliar testes de concorrência, persistência e exclusão.
- [ ] Definir login e autorização por usuário com a frente 3; a base atual é de operador único.
- [ ] Integrar templates/arquivos estáticos quando entregues pela frente 4.

**Pronto quando:** o contrato atende à interface e o acesso aos dados segue o modelo de usuários efetivamente implementado.

## Frente 2 — Próximas tarefas

- [ ] Validar todas as categorias planejadas com casos vulneráveis, corrigidos e falsos positivos.
- [ ] Documentar os formatos e versões de dependências cobertos; adicionar exemplos com versões resolvidas.
- [ ] Ampliar testes de saída inválida, falhas de rede, interrupções e limpeza de recursos.
- [ ] Completar isolamento e limites de recursos. Separação de processos, timeout e limites de tamanho não são um sandbox completo.
- [ ] Integrar os sinais de manutenção fornecidos pela frente 3.

**Pronto quando:** cobertura e limites estão demonstrados e os problemas são apresentados com evidências, prioridades e incertezas corretas.

## Frente 3 — Próximas tarefas

- [ ] Testar repositório privado próprio autorizado, paginação e revogação da instalação.
- [ ] Apoiar o login/autorização individual sem editar simultaneamente arquivos da frente 1.
- [ ] Associar cada dependência ao repositório e aos canais oficiais corretos.
- [ ] Coletar avisos explícitos dos mantenedores e status de arquivamento, com fonte e data.
- [ ] Verificar sucessores e mudanças de endereço antes de recomendar substituições.
- [ ] Avaliar alternativas por adequação, manutenção, licença e esforço de migração; informar quando não houver candidata verificada.

**Pronto quando:** o acesso é autorizado e os sinais de manutenção têm evidências verificáveis. Inatividade isolada não deve gerar diagnóstico de abandono.

## Frente 4 — Próximas tarefas

- [ ] Seleção de repositório, confirmação da autorização e início manual.
- [ ] Acompanhamento de execução e mensagens para falhas/verificações não realizadas.
- [ ] Achados por tipo e prioridade, com evidências, confiança e ações sugeridas, sem notas ou scores.
- [ ] Exibição do commit e da data/hora.
- [ ] Histórico e exclusão com confirmação.
- [ ] Revisão em desktop e celular e integração com API real.

**Pronto quando:** o usuário consegue percorrer o fluxo completo sem que dados simulados sejam apresentados como resultados reais. Credenciais reais não devem ser embutidas no frontend.

## Decisões adiadas e entrega

- Provedor/modelo de IA, custos e autorização de envio dos dados mínimos.
- Publicação e acesso dos jurados por link, a resolver antes da submissão conforme o regulamento.
- Vídeo, links e revisão final dos requisitos do evento.
- Validação da matriz de Python: declarado 3.11+, testado até aqui em 3.14.10 no Linux.
- Avisos/licenças das dependências e estratégia de reprodutibilidade da instalação Python.
- Aviso de depreciação do TestClient/httpx: não bloqueia os testes atuais, mas deve ser acompanhado.

Monitoramento contínuo, análise externa, disparo por GitHub Actions ou outras automações e planos comerciais continuam fora desta primeira entrega.

## Referências

- [Proposta e decisões](PROJETO.md)
- [Guia de implementação](IMPLEMENTACAO.md)
- [Configuração e testes do GitHub](GITHUB.md)
- [Divisão das frentes](FRENTES-DE-TRABALHO.md)
- [Rascunho do evento](RASCUNHO.md)
- [Regulamento consultado](regulamento-atual.md)
