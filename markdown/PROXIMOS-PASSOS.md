# Próximos passos do CyberCheck

O planejamento principal está definido. A prioridade agora é implementar e validar o programa. Hospedagem e provedor de IA ficam para depois, sem bloquear o trabalho.

## Referências

- [PROJETO.md](PROJETO.md): proposta e decisões confirmadas.
- [IMPLEMENTACAO.md](IMPLEMENTACAO.md): orientações técnicas, ferramentas e limites.
- [RASCUNHO.md](RASCUNHO.md): apresentação do problema e do objetivo para o evento.
- [Regulamento atual](regulamento-atual.md): requisitos de participação e entrega.

## 1. Preparar a base do programa

- Criar a aplicação Python com FastAPI, páginas Jinja2 e SQLite.
- Separar o programa do site de apresentação que já existe em `../website/`.
- Documentar instalação, configuração e execução, sem incluir segredos no repositório.
- Definir as versões das ferramentas e conferir suas licenças e avisos de terceiros.

**Resultado esperado:** aplicação inicia e permite navegar entre projetos e histórico de análises, incluindo estados vazios claros.

## 2. Validar as três ferramentas

- Preparar exemplos próprios e controlados de código inseguro e corrigido, dependências afetadas e credenciais fictícias.
- Rodar Bandit, OSV-Scanner e Betterleaks, verificando seus formatos de saída e limites.
- Escolher regras e arquivos de dependências suportados na primeira entrega.
- Garantir que a análise não execute o código, os builds ou os scripts do projeto avaliado.
- Verificar o mascaramento de segredos em relatórios, logs e eventuais dados destinados à IA.

**Resultado esperado:** saber quais problemas conseguimos apontar com evidências, quais casos geram falsos positivos e o que não está coberto.

## 3. Integrar o GitHub

- Configurar uma GitHub App com permissões de leitura necessárias e seleção de repositórios pelo usuário.
- Implementar autenticação e autorização para acesso a repositórios públicos e privados.
- Obter a revisão exata escolhida para análise e registrar o SHA completo do commit.
- Manter credenciais de acesso protegidas e impedir acesso aos projetos de outros usuários.

**Resultado esperado:** o usuário conecta o GitHub e seleciona um repositório autorizado para analisar.

## 4. Implementar a execução das análises

- Criar a solicitação manual de análise e executá-la em processo separado.
- Definir coordenação persistente, isolamento, limites de tempo e recursos e tratamento de falhas.
- Obter o código em uma cópia temporária e descartá-la ao terminar, inclusive em caso de erro.
- Registrar commit, data/hora com fuso, ferramentas, versões e cobertura efetivamente executada.
- Distinguir execução completa, parcial e com falha, sem apresentar ausência de resultados como ausência de problemas.

**Resultado esperado:** iniciar uma análise, acompanhar seu estado e obter resultados reais das ferramentas.

## 5. Apresentar e guardar os problemas

- Agrupar os achados por tipo e organizá-los por prioridade, sem notas ou scores.
- Usar crítica, alta, média e baixa com justificativa; quando faltar informação, indicar “prioridade a revisar”.
- Exibir evidência, localização quando aplicável, possível impacto, confiança e ação sugerida.
- Manter os relatórios vinculados ao commit e à data da análise.
- Permitir que o usuário consulte e exclua seus relatórios e evidências associadas.

**Resultado esperado:** compreender o que foi encontrado e o que pode ser feito, sem confundir suspeita com vulnerabilidade confirmada.

## 6. Avaliar dependências descontinuadas

- Associar corretamente cada pacote ao repositório e aos canais oficiais dos mantenedores.
- Consultar os dois sinais aprovados: aviso explícito de abandono/descontinuação e repositório arquivado.
- Apresentar fonte e data, verificando se há sucessor ou mudança de endereço.
- Sugerir alternativas somente com evidências de adequação, manutenção e licença, explicando limites e diferenças de migração.
- Não usar inatividade isolada como prova de abandono nem inventar uma substituição quando não houver candidata adequada.

**Resultado esperado:** alertar sobre esses sinais e apoiar a decisão de manter, atualizar ou substituir uma dependência.

## 7. Verificar o fluxo completo

- Testar conexão com GitHub, seleção de repositório, início da análise, resultados e exclusão do histórico.
- Conferir autorização entre usuários e tratamento de erros e interrupções.
- Comparar análises dos exemplos vulneráveis e corrigidos.
- Revisar a interface em desktop e celular.
- Atualizar a documentação com a cobertura real e os limites encontrados.

**Resultado esperado:** um fluxo demonstrável, com resultados verificáveis e sem funcionalidades simuladas apresentadas como prontas.

## 8. Retomar as decisões adiadas e preparar a entrega

- Escolher provedor/modelo de IA quando houver condições de avaliar custos e tratamento de dados; ativar somente após definir o envio autorizado dos dados mínimos.
- Definir hospedagem e acesso à demo depois de implementar o programa.
- Preparar o vídeo e os links de entrega conforme o regulamento.
- Conferir elegibilidade dos repositórios, licenças, prazos e regras de congelamento antes da submissão.

Monitoramento contínuo, execução automática por GitHub Actions ou outras automações, análise externa e planos comerciais continuam como evoluções futuras.
