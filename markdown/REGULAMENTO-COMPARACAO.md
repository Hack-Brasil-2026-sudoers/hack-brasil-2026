# Comparação do regulamento do Hack Brasil 2026

Consulta ao [site oficial](https://hackbrasil.com/regulamento) em 15/11/2026.

- Base anterior: [regulamento.md](regulamento.md), com atualização declarada de 02/11/2026. Arquivo preservado.
- Versão atual: [regulamento-atual.md](regulamento-atual.md), transcrita da página que informa atualização de 09/11/2026.
- A comparação identifica diferenças entre a cópia local e o texto atual; não estabelece a data individual de cada alteração nem pressupõe um histórico oficial de mudanças.

## Ferramentas: regras mantidas

As cláusulas 6.3 a 6.7 mantêm o conteúdo da cópia anterior:

- **6.3:** livre escolha de tecnologias; nenhum produto de patrocinador, parceiro ou terceiro é obrigatório para participar, ser avaliado ou receber prêmio.
- **6.4:** ferramentas de IA são permitidas e recomendadas.
- **6.5:** bibliotecas, frameworks, APIs e código aberto são permitidos, respeitando suas licenças e os direitos de uso.
- **6.6:** licença open source é recomendada, mas não obrigatória; os jurados precisam poder ler, executar e testar o código.
- **6.7:** repositórios entregues devem permanecer públicos e acessíveis pelo menos até 15 de dezembro.

A cláusula 10.4 também mantém a independência dos prêmios em relação ao uso ou à contratação de produtos dos patrocinadores. Portanto, não há obrigação de usar Firecrawl, Resend, Devin ou um provedor específico de IA.

## Diferenças encontradas

| Item atual | Cópia anterior | Texto atual / mudança |
| --- | --- | --- |
| 1.3 | Finalidade cultural, educativa e tecnológica, gratuidade e avaliação pelo júri | Acrescenta enquadramento legal do concurso cultural e declaração de que dados dos participantes não são vendidos nem cedidos para fins comerciais |
| 2 | Anúncio do júri e dos quadros de prêmios até 30/11 | Passa a mencionar apenas o anúncio do júri nesse ponto; principais datas permanecem |
| 5.1 | Limites das trilhas somados às proibições gerais | Esclarece a diferença entre não se enquadrar em uma trilha e ser proibido em todas |
| 6.1 | Repositórios novos após 04/11 às 21h, sem histórico anterior | Acrescenta que todo código desenvolvido durante o evento deve estar nesses repositórios e proíbe explicitamente forks |
| 6.2 | Exceção para código aberto já público antes do evento | Explicita a proibição de importar código privado anterior, inclusive do próprio time; permite dependência ou cópia de código aberto elegível, sem histórico original e com origem indicada na mensagem do commit de cópia |
| 6.8 | Remetia às categorias proibidas do FAQ e restrições das trilhas | Incorpora a lista no regulamento e esclarece que projetos de proteção relacionados a esses assuntos não são proibidos apenas por mencioná-los; finalidade e uso facilitado são relevantes |
| 6.9 | Saúde com dados sintéticos; finanças com teste/simulação; segurança em sistemas próprios ou autorizados | Ajusta a redação de finanças para permitir demo em teste/simulação em vez de transações reais; as exigências de segurança e de não expor dados pessoais permanecem |
| 7.1 | Prazo de submissão e última versão enviada | Explicita que a avaliação online considera o último commit enviado ao GitHub até o prazo; commits posteriores não contam |
| 7.2 e 9.8 | Vídeo em português ou inglês, com preferência por inglês | Remove preferência: submissão, vídeo e apresentação podem ser em português ou inglês, sem influência na nota, com garantia de jurados que entendam português |
| 8.1 e 9.4 | Nota mínima a definir pelo júri | Define mínimo de 20/40 pontos na fase online para chegar à final |
| 8.3 | Regras específicas da final informadas no local | Passam a ser enviadas por e-mail com o anúncio dos finalistas, antes da confirmação de presença |
| 8.4 | Não havia cláusula de congelamento | Finalistas não podem alterar código ou fazer commits nos repositórios entregues entre o encerramento de 30/11 às 23h59 e o início da final; podem preparar apresentação e manter a demo sem mudar código; desenvolvimento recomeça na final de 12/12 |
| 9.1 a 9.4 | Quatro critérios de mesmo peso, sem escala detalhada | Mantém critérios, esclarece impacto e define notas de 0 a 10 por critério, soma de até 40 e média entre jurados; na final, novas notas partem do zero |
| 10.1 | Classificação definida pelo júri | Explicita que os três primeiros lugares são da classificação geral, entre trilhas, e vincula prêmios de finalistas à participação na final |
| 10.3 | Prêmios sem alguns benefícios atuais | Acrescenta créditos de participação Firecrawl/Devin, benefícios Nvoip e Globalfy, sujeitos às condições descritas; também modifica a descrição de comunicação das condições de entrega pelos patrocinadores |
| 10.6 | Organização não responde pela entrega de prêmios de patrocinadores | Explicita atrasos/falhas e inclui parceiros |
| 13.1 | Descrição geral de compartilhamento de dados | Detalha destinatários, dados e finalidades; veda uso desses compartilhamentos para publicidade ou outros fins próprios |
| 14.1 | Poder de alterar o regulamento com aviso | Limita alterações após 04/11 aos casos descritos e declara que não reduzem prêmios nem criam restrição nova para projetos já enviados na submissão final |

Houve renumeração nas seções 8 e 9 e atualização de referências internas. A renumeração, isoladamente, não indica mudança material.

## Aplicação ao CyberCheck

Interpretação para orientar o projeto, a partir das cláusulas citadas:

- Podemos escolher analisadores especializados e serviços de IA conforme adequação e licença. Não há stack obrigatória.
- O propósito deve continuar defensivo. A trilha de cibersegurança (5.2) exclui malware, exploits e ferramentas feitas para invadir, espionar ou escapar de detecção. Os testes devem ocorrer em sistemas próprios ou com autorização por escrito (5.2 e 6.9).
- Para a demonstração, usar projetos próprios controlados, credenciais fictícias e dados sintéticos. Não expor dados pessoais reais de terceiros (6.9).
- O código do CyberCheck entregue ao evento precisa ser público conforme 6.1 e 6.7. Isso não significa que todos os repositórios analisados pelo produto precisem ser públicos: são papéis distintos. O tratamento dos repositórios privados continua exigindo autorização e definição de acesso e dados.
- Antes de copiar código externo ou escolher ferramentas, verificar licença, origem e as condições de reutilização de 6.2 e 6.5. Usar uma biblioteca não deve ser confundido com entregar um fork como repositório do projeto.
- Planejar a entrega até 30/11 às 23h59, com demo e vídeo de até três minutos. Caso o time seja finalista, respeitar o congelamento de código até a final.

Este levantamento não verificou a data de criação do repositório do time, a elegibilidade de cada commit, nem as licenças de ferramentas ainda não escolhidas. Termos de Uso e Política de Privacidade vinculados pelo regulamento não foram comparados.
