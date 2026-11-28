# ADR 0002: Go e Rust como linguagens do laboratório

- **Status:** aceita
- **Data:** 2026-11-27
- **Experimento de origem:** E4 (`specs/003-localidades-java/`), que comparou o serviço de localidades em Java com o E1, em Python.

## Contexto
A constituição 1.0.0 limitava o projeto a Python e Java. O E4 mostrou que a régua montada no E1 funciona para comparar linguagens: um contrato OpenAPI escrito à mão, uma suíte de caixa-preta que só fala com o serviço pela rede e um script de medição. O mesmo serviço foi reimplementado sem mudar o contrato, passou nos mesmos 82 cenários e teve partida, memória, latência e ergonomia medidas com o mesmo método.

A comparação também mostrou de onde vêm os custos. As cinco convergências do E4 acharam só comportamentos padrão do Tomcat e do Spring que o contrato não previa. A latência empatou, e a diferença ficou no custo fixo do ecossistema: 0,14 s e 55 MB no Python, contra 1,0 s e 261 MB no Java.

O projeto é um laboratório. Com a régua pronta, aplicá-la a mais dois ecossistemas custa pouco e responde perguntas que só a medição responde:
- **Go:** binário único, biblioteca padrão com servidor HTTP, ciclo rápido e curva de aprendizado curta.
- **Rust:** o extremo de eficiência e de garantias em tempo de compilação, em troca do maior esforço de construção.

## Decisão
1. **Linguagens permitidas:** Python 3.11+, Java 25 (LTS, confirmado no E4), Go e Rust. TypeScript continua fora. A constituição passa para a versão **1.1.0**.
2. **Versões de Go e Rust:** a estável vigente, confirmada na documentação oficial no início de cada experimento e registrada no plano, como o E4 fez com o JDK.
3. **Linguagem nova entra por experimento:** a primeira vez de uma linguagem é um experimento com pergunta, timebox e `RESULTS.md`. De preferência, ele reimplementa um serviço que já tem contrato e suíte, para comparar com a mesma régua.
4. **Próximos experimentos:** **E7**, o serviço de localidades em Go, e **E8**, o mesmo serviço em Rust. Os dois vêm logo depois do E4, com o mesmo contrato, a mesma suíte de caixa-preta e o mesmo `medir.sh`, estendido para quatro implementações.
5. **Sem serviço permanente sem necessidade:** nenhum serviço definitivo nasce em Go ou Rust só porque a linguagem foi permitida (princípio X).

## Alternativas consideradas
- **Só Go:** a linguagem de menor custo de entrada, e a sugestão inicial, de uma linguagem por vez. Foi descartada porque o laboratório ganha mais com o contraste completo: Go como meio-termo, Rust como extremo. Os dois experimentos continuam separados, um de cada vez, e não somam infraestrutura.
- **Kotlin ou outra linguagem da JVM:** compartilharia o runtime com o E4, e a comparação diria pouco de novo sobre partida e memória.
- **TypeScript (Node):** continua fora do escopo, como na 1.0.0. O laboratório não tem frente de frontend que justifique a linguagem agora.
- **Manter Python e Java:** encerraria a pergunta de ecossistemas com só dois pontos de comparação, justo quando a régua ficou pronta.

## Consequências
- **Fica mais fácil:** comparar quatro implementações do mesmo contrato com o mesmo método. A suíte de caixa-preta e as fixtures já existem e não dependem de linguagem.
- **Fica mais difícil:** manter mais duas cadeias de ferramentas (`go`, e `cargo` com `rustup`) instaladas e atualizadas, com a verificação de testes sem rede (princípio IV) em cada uma.
- **A revisitar:**
  - depois do E7 e do E8, se alguma das quatro implementações "se gradua" para `services/` (decisão em aberto desde o E4);
  - se o `medir.sh` precisa ser generalizado para N implementações;
  - se a ordem do roteiro (E7 e E8 antes do E2) ainda faz sentido.
