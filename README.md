# Laboratório Brasil Aberto

Laboratório pessoal para explorar o Brasil por meio de dados públicos e fontes oficiais, e experimentar tecnologias em Python, Java, Go e Rust com desenvolvimento orientado por especificação ([Spec Kit](https://github.com/github/spec-kit)).

Explorar → coletar → entender → experimentar → comparar → decidir.

## O que já vem pronto
- Spec Kit inicializado para o **Claude Code** (skills em `.claude/skills/`, templates e scripts em `.specify/`).
- **Constituição** do projeto em `.specify/memory/constitution.md`, baseada nos princípios do documento de discovery.
- **Catálogo inicial de fontes** em `discovery/sources.json`, com grau de verificação por fonte, e template de ficha em `discovery/fichas/`.
- **Roteiro** de experimentos (`docs/roteiro.md`), prompt pronto do E0 (`docs/prompts/`), templates de resultados e ADR, e o ADR 0001 (rascunho) com as convenções de API.

## Preparação (macOS)
1. Instale as ferramentas, se ainda não tiver:
   ```bash
   brew install uv git
   brew install --cask visual-studio-code
   ```
   Python 3.11 ou superior é necessário. O JDK só será preciso a partir do E4.
2. Instale o Claude Code (incluído nos planos pagos do Claude) e confirme com `claude --version`:
   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   # ou: brew install --cask claude-code
   ```
   Documentação oficial: https://code.claude.com/docs/en/setup. Se preferir usar dentro do editor, há também a extensão do Claude Code para o VS Code.
3. Inicialize o git, porque o Spec Kit cria uma branch por funcionalidade:
   ```bash
   cd laboratorio-brasil-aberto
   git init && git add . && git commit -m "Kit inicial"
   ```
4. Se quiser o CLI do Spec Kit na sua máquina (para atualizar templates, adicionar presets ou integrações):
   ```bash
   uv tool install specify-cli
   ```
   Este kit foi gerado com o Spec Kit `1.4.1.dev0`, logo depois da versão estável `v1.4.0` (10/11/2026). Para fixar uma versão, siga o guia de instalação: https://github.github.io/spec-kit/installation.html

## Como conduzir um experimento
1. Abra a pasta no VS Code e rode `claude` no terminal, na raiz.
2. A constituição já está escrita. Se quiser refinar, use `/speckit-constitution`.
3. Siga o arquivo `docs/prompts/E0-inventario-fontes.md`: `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, revise, `/speckit-implement` e `/speckit-converge`. O converge compara o código com a spec, o plano e as tarefas e cria tarefas para o que faltar: alterne implement e converge até ele responder `Converged`.
   - Portões de qualidade opcionais, para funcionalidades maiores: `/speckit-clarify` (antes do plano), `/speckit-checklist` e `/speckit-analyze` (coerência entre spec, plano e tarefas).
   - Se o fluxo completo ficar pesado para experimentos pequenos, experimente o preset enxuto: `specify preset add lean` (requer o CLI do passo 4). Ele troca os templates longos por prompts curtos, com menos estrutura e menos tokens.
4. Rode o resultado localmente (as fontes públicas são acessadas da sua máquina), guarde o relatório em `discovery/reports/` e preencha o `RESULTS.md`.
5. Traga o relatório para a conversa para revisarmos as hipóteses e decidirmos o próximo experimento.

## Segredos
Chaves e tokens ficam em `.env` (veja `.env.example`) e nunca são versionados.

## Aviso
Os dados e as classificações de acesso deste repositório são hipóteses até a verificação. Respostas jurídicas e financeiras produzidas com estas ferramentas não substituem aconselhamento profissional.
