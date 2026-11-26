from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

from contrato import OPENAPI


def test_openapi_e_valido():
    documento, _ = read_from_filename(str(OPENAPI))
    validate(documento)
