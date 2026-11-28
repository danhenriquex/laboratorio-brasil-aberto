# Contratos do E7

O E7 cumpre o **mesmo contrato** do E1 e do E4, sem mudanças (Constituição VI: compartilha-se o contrato, nunca o código):

- [contracts/localidades/openapi.yaml](../../../contracts/localidades/openapi.yaml): contrato HTTP v1 (OpenAPI 3.1).
- [contracts/localidades/README.md](../../../contracts/localidades/README.md): rotas, configuração comum (`LOCALIDADES_*`) e verificação de caixa-preta.

O critério de pronto é `contracts/localidades/verificacao/verificar.sh "experiments/go/localidades/localidades"` passando em todos os cenários, os mesmos 82 que passam no E1 e no E4.
