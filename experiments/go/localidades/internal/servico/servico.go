// Package servico tem os casos de uso do serviço de localidades. Não importa net/http (portas e adaptadores,
// como no E1 e no E4).
package servico

import (
	"context"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/dominio"
)

const (
	FonteNome       = "IBGE — API de localidades"
	URLDocumentacao = "https://servicodados.ibge.gov.br/api/docs/localidades"
)

// layoutMomento escreve sempre os milissegundos e, em UTC, o sufixo Z. O time.RFC3339Nano cortaria os zeros
// à direita e quebraria o padrão \.\d{3}Z do contrato (data-model do E7).
const layoutMomento = "2006-01-02T15:04:05.000Z07:00"

func FormatarMomento(t time.Time) string { return t.UTC().Format(layoutMomento) }

// Meta é a procedência de toda resposta (Constituição II).
type Meta struct {
	Fonte           string `json:"fonte"`
	URLFonte        string `json:"url_fonte"`
	URLDocumentacao string `json:"url_documentacao"`
	ColetadoEm      string `json:"coletado_em"`
	Desatualizado   bool   `json:"desatualizado"`
}

func NovaMeta(urlFonte string, coletadoEm time.Time, desatualizado bool) Meta {
	return Meta{
		Fonte:           FonteNome,
		URLFonte:        urlFonte,
		URLDocumentacao: URLDocumentacao,
		ColetadoEm:      FormatarMomento(coletadoEm),
		Desatualizado:   desatualizado,
	}
}

// Fonte é a porta para o IBGE; o cliente de internal/fonte a implementa.
type Fonte interface {
	Estados(ctx context.Context) ([]dominio.UF, string, error)
	MunicipiosDaUF(ctx context.Context, codigoUF string) ([]dominio.MunicipioResumido, string, error)
	Municipio(ctx context.Context, codigo string) (dominio.Municipio, string, error)
}

// Resultado é o que um caso de uso devolve ao adaptador HTTP. Cache é acerto, falta ou desatualizado.
type Resultado struct {
	Dados     any
	Meta      Meta
	Paginacao *dominio.Paginacao
	Cache     string
}

// Opcoes da montagem do serviço. Os relógios são injetáveis para os testes não esperarem de verdade.
type Opcoes struct {
	Agora      func() time.Time
	Monotonico func() time.Duration
	Validade   time.Duration
	ItensMax   int
}

type Servico struct {
	fonte  Fonte
	opcoes Opcoes
}

func Novo(fonte Fonte, opcoes Opcoes) *Servico {
	if opcoes.Agora == nil {
		opcoes.Agora = time.Now
	}
	if opcoes.Monotonico == nil {
		inicio := time.Now()
		opcoes.Monotonico = func() time.Duration { return time.Since(inicio) }
	}
	return &Servico{fonte: fonte, opcoes: opcoes}
}

// obtido é um recurso do IBGE já normalizado, com a procedência e o uso da cópia guardada.
type obtido struct {
	dados any
	meta  Meta
	cache string
}

type buscar func(ctx context.Context) (any, string, error)

// obter chama a fonte direto. A cópia guardada e a consulta compartilhada entram na US3 (T027).
func (s *Servico) obter(ctx context.Context, _ string, b buscar) (obtido, error) {
	coletadoEm := s.opcoes.Agora()
	dados, url, err := b(ctx)
	if err != nil {
		return obtido{}, err
	}
	return obtido{dados: dados, meta: NovaMeta(url, coletadoEm, false), cache: "falta"}, nil
}
