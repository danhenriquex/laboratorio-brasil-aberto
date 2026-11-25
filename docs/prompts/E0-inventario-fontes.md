# E0: inventário e conectividade das fontes

Timebox sugerido: 1 a 2 sessões curtas. Linguagem: Python (decidida no plano, não na spec).

## 1. Cole no `/speckit-specify`

Quero uma ferramenta de linha de comando que catalogue e avalie fontes públicas brasileiras de dados, para que eu entenda quais podem ser integradas de forma sustentável antes de construir serviços.

Usuário-alvo: eu mesmo, como desenvolvedor do laboratório, rodando localmente.

O que ela deve fazer:
- Ler um catálogo de fontes (`discovery/sources.json`) com nome, domínio, URL da documentação, URL de teste quando existir, tipo de dado e hipótese de acesso.
- Para cada fonte com URL de teste, fazer uma requisição e registrar: status HTTP, latência, formato da resposta (JSON, CSV, XML, HTML), tamanho, e se exigiu autenticação.
- Inspecionar uma amostra da resposta e registrar a estrutura (campos e tipos), sem guardar dados pessoais.
- Registrar a data e a hora da coleta em cada resultado.
- Tratar sem travar: timeout, fonte indisponível, resposta inválida, redirecionamento, bloqueio ou limite de requisições.
- Respeitar as fontes: uma requisição por fonte por execução, com intervalo entre elas, sem paralelismo agressivo.
- Gerar relatórios em JSON e em HTML legível, com um indicador de grau de verificação por fonte (confirmado, parcial, não verificado) e a diferença entre a hipótese de acesso e o resultado observado.
- Não pular fontes sem URL de teste: elas aparecem no relatório como "sem teste automatizado", com o link da documentação para verificação manual.

Cenários de aceitação:
- Fonte responde normalmente: relatório mostra status, latência e estrutura da amostra.
- Fonte fora do ar ou lenta: relatório mostra a falha com a causa, e a execução continua com as demais.
- Fonte exige chave: relatório marca "exige autenticação" sem tentar contornar.
- Fonte devolve formato inesperado: relatório registra o formato observado.

Fora do escopo: contornar autenticação, coletar dados em volume, qualquer chamada que escreva ou altere dados nas fontes.

## 2. Depois, no `/speckit-plan`
Python 3.11+, `httpx` para requisições, `pytest` com `respx` para os testes sem rede, `uv` para dependências. Estrutura em `experiments/python/discovery/`. Relatórios em `discovery/reports/`. Siga a constituição, em especial os princípios III (verificar antes de afirmar), IV (testes sem rede) e V (resiliência).

## 3. Depois
`/speckit-tasks`, revise a lista, `/speckit-implement` e `/speckit-converge` (repita os dois até o converge responder `Converged`). Quando funcionar, rode localmente, guarde o relatório em `discovery/reports/` e preencha uma ficha em `discovery/fichas/` para cada fonte da rodada 1 (IBGE, BCB, Câmara).

## 4. Fechamento
Copie `docs/templates/RESULTS.md` para a pasta da feature em `specs/` e preencha. Traga o relatório para a conversa: com ele, revisamos as hipóteses de acesso e decidimos o E1.
