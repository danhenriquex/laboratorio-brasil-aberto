# Contratos do E4

O E4 cumpre o **mesmo contrato** do E1, sem mudanças (Constituição VI: compartilha-se o contrato, nunca o código):

- [contracts/localidades/openapi.yaml](../../../contracts/localidades/openapi.yaml): contrato HTTP v1 (OpenAPI 3.1).
- [contracts/localidades/README.md](../../../contracts/localidades/README.md): rotas, configuração comum (`LOCALIDADES_*`) e verificação de caixa-preta.

O critério de pronto é `contracts/localidades/verificacao/verificar.sh "java -jar experiments/java/localidades/target/localidades.jar"` passando em todos os cenários.
