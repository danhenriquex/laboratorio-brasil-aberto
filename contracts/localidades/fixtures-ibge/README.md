# Fixtures da API de localidades do IBGE

Respostas usadas pelos testes do E1 e pelo IBGE falso da suíte de verificação. São dados públicos de unidades territoriais, sem dados pessoais.

## Respostas reais

Gravadas por [`gravar.py`](gravar.py) em **2026-11-26 16:06:38 UTC**, com o User-Agent `laboratorio-brasil-aberto-localidades/0.1.0`, uma chamada por recurso e 2 s de intervalo. Os corpos estão exatamente como foram recebidos.

| Arquivo | URL | Status | Bytes | SHA-256 |
|---|---|---|---|---|
| `estados.json` | `https://servicodados.ibge.gov.br/api/v1/localidades/estados` | 200 | 2446 | `7ca1368dea3af83cba1af84ae8a7e88f1173c97586831d086cc8b3c1ba9c6596` |
| `municipios-uf-33.json` | `…/estados/33/municipios` (RJ) | 200 | 43116 | `9259126c654f7825fe7228a8070bb1775b4a5f6f283ea2b33738c588c6991c12` |
| `municipios-uf-35.json` | `…/estados/35/municipios` (SP) | 200 | 284370 | `c06b7327c3bf7475d0c63c90c5f8c9122464fd0ed84bc98709a2a7f82649d14b` |
| `municipios-uf-53.json` | `…/estados/53/municipios` (DF) | 200 | 467 | `2fe679ffa023400bbcfabdb4c2611cc736a23a3bc8a99ca7671ad13af91153e8` |
| `municipio-5101837.json` | `…/municipios/5101837` | 200 | 268 | `602d721d7f2e46eb945f7ef0d09abec07033bbba830c56078ab884f5c7dc15cd` |

O que elas contêm:
- 27 UFs;
- RJ com 92 municípios, SP com 645 e DF com 1 (Brasília, `5300108`);
- `5101837` é Boa Esperança do Norte (MT), com `microrregiao: null`.

Os itens das listas por UF têm a mesma forma que a resposta de `/municipios/{codigo}`. Por isso o IBGE falso monta a consulta por código a partir delas.

## Fixtures sintéticas

| Arquivo | O que simula |
|---|---|
| `erro.html` | página HTML de erro devolvida com status 200 |
| `municipio-sem-regiao-imediata.json` | o item de `3304557` (Rio de Janeiro) sem a chave `regiao-imediata` |
| `estados-sem-regiao.json` | `estados.json` com o primeiro item sem `regiao` |

## Quando regravar

Só quando o IBGE mudar a forma das respostas. Nesse caso, regrave e atualize esta tabela com a nova data. Os testes automatizados nunca chamam o IBGE real.
