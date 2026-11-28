# Contratos do E8

O E8 cumpre o **mesmo contrato** do E1, do E4 e do E7, sem mudanças (Constituição VI: compartilha-se o contrato, nunca o código):

- [contracts/localidades/openapi.yaml](../../../contracts/localidades/openapi.yaml): contrato HTTP v1 (OpenAPI 3.1).
- [contracts/localidades/README.md](../../../contracts/localidades/README.md): rotas, configuração comum (`LOCALIDADES_*`) e verificação de caixa-preta.

O critério de pronto é `contracts/localidades/verificacao/verificar.sh "experiments/rust/localidades/target/release/localidades"` passando em todos os cenários, os mesmos 82 que passam nas outras três implementações.
