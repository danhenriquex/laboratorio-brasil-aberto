package servico

import (
	"testing"
	"time"
)

func TestFormatarMomentoComMilissegundosEZ(t *testing.T) {
	casos := []struct {
		momento  time.Time
		esperado string
	}{
		{time.Date(2026, 11, 26, 12, 0, 0, 0, time.UTC), "2026-11-26T12:00:00.000Z"},
		{time.Date(2026, 11, 26, 12, 0, 0, 123_456_789, time.UTC), "2026-11-26T12:00:00.123Z"},
		{time.Date(2026, 11, 26, 9, 0, 0, 5_000_000, time.FixedZone("BRT", -3*3600)), "2026-11-26T12:00:00.005Z"},
	}
	for _, c := range casos {
		if obtido := FormatarMomento(c.momento); obtido != c.esperado {
			t.Errorf("FormatarMomento(%v) = %q, esperado %q", c.momento, obtido, c.esperado)
		}
	}
}

func TestNovaMetaComAProcedencia(t *testing.T) {
	m := NovaMeta("https://exemplo/estados", time.Date(2026, 11, 26, 12, 0, 0, 0, time.UTC), true)
	if m.Fonte != "IBGE — API de localidades" || m.URLDocumentacao != "https://servicodados.ibge.gov.br/api/docs/localidades" ||
		m.URLFonte != "https://exemplo/estados" || m.ColetadoEm != "2026-11-26T12:00:00.000Z" || !m.Desatualizado {
		t.Errorf("meta = %+v", m)
	}
}
