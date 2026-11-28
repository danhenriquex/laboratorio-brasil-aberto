// Package servico tem os casos de uso do serviço de localidades. Não importa net/http (portas e adaptadores,
// como no E1 e no E4).
package servico

import (
	"context"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/cache"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/dominio"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/erros"
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
	cache  *cache.Cache
}

func Novo(fonte Fonte, opcoes Opcoes) *Servico {
	if opcoes.Agora == nil {
		opcoes.Agora = time.Now
	}
	if opcoes.Monotonico == nil {
		inicio := time.Now()
		opcoes.Monotonico = func() time.Duration { return time.Since(inicio) }
	}
	return &Servico{fonte: fonte, opcoes: opcoes, cache: cache.Novo(opcoes.Agora, opcoes.Monotonico, opcoes.Validade)}
}

// obtido é um recurso do IBGE já normalizado, com a procedência e o uso da cópia guardada.
type obtido struct {
	dados any
	meta  Meta
	cache string
}

type buscar = cache.Buscar

// obter passa pela cópia guardada: o meta vem da entrada (coletado_em da consulta original e desatualizado),
// e o resultado da cópia (acerto, falta, desatualizado) segue para as métricas e o registro.
func (s *Servico) obter(ctx context.Context, chave string, b buscar) (obtido, error) {
	e, err := s.cache.Obter(ctx, chave, b)
	if err != nil {
		return obtido{}, err
	}
	return obtido{dados: e.Dados, meta: NovaMeta(e.URLFonte, e.ColetadoEm, e.Desatualizado), cache: e.Resultado}, nil
}

// --- US1 ---

func (s *Servico) estados(ctx context.Context) (obtido, error) {
	return s.obter(ctx, "estados", func(ctx context.Context) (any, string, error) {
		return s.fonte.Estados(ctx)
	})
}

// ListarUFs devolve as 27 UFs ordenadas por nome.
func (s *Servico) ListarUFs(ctx context.Context) (Resultado, error) {
	o, err := s.estados(ctx)
	if err != nil {
		return Resultado{}, err
	}
	return Resultado{Dados: dominio.Ordenar(o.dados.([]dominio.UF)), Meta: o.meta, Cache: o.cache}, nil
}

// ObterUF resolve a sigla ou o código antes de consultar, para entrada inválida não chegar ao IBGE.
func (s *Servico) ObterUF(ctx context.Context, param string) (Resultado, error) {
	codigo, err := dominio.ResolverUF(param)
	if err != nil {
		return Resultado{}, err
	}
	o, err := s.estados(ctx)
	if err != nil {
		return Resultado{}, err
	}
	for _, uf := range o.dados.([]dominio.UF) {
		if uf.Codigo == codigo {
			return Resultado{Dados: uf, Meta: o.meta, Cache: o.cache}, nil
		}
	}
	return Resultado{}, erros.RespostaInesperadaDaFonte("a UF %s não veio na lista de UFs do IBGE", codigo)
}

// ListarMunicipios valida, resolve a UF, consulta, filtra pelo nome (se houver), ordena e pagina, na
// mesma ordem do E1. nome nil significa "sem filtro".
func (s *Servico) ListarMunicipios(ctx context.Context, paramUF string, pagina int64, itens int, nome *string) (Resultado, error) {
	if err := dominio.ValidarPaginacao(pagina, itens, s.opcoes.ItensMax); err != nil {
		return Resultado{}, err
	}
	var filtro string
	if nome != nil {
		valido, err := dominio.ValidarNome(*nome)
		if err != nil {
			return Resultado{}, err
		}
		filtro = valido
	}
	codigo, err := dominio.ResolverUF(paramUF)
	if err != nil {
		return Resultado{}, err
	}
	o, err := s.obter(ctx, "estados/"+codigo+"/municipios", func(ctx context.Context) (any, string, error) {
		return s.fonte.MunicipiosDaUF(ctx, codigo)
	})
	if err != nil {
		return Resultado{}, err
	}
	municipios := o.dados.([]dominio.MunicipioResumido)
	if nome != nil {
		municipios = dominio.FiltrarPorNome(municipios, filtro)
	}
	p := dominio.Paginar(dominio.Ordenar(municipios), pagina, itens)
	return Resultado{Dados: p.Itens, Meta: o.meta, Paginacao: &p.Paginacao, Cache: o.cache}, nil
}

// --- US2 ---

// ObterMunicipio valida o código antes de consultar o IBGE.
func (s *Servico) ObterMunicipio(ctx context.Context, codigo string) (Resultado, error) {
	codigo, err := dominio.ValidarCodigoMunicipio(codigo)
	if err != nil {
		return Resultado{}, err
	}
	o, err := s.obter(ctx, "municipios/"+codigo, func(ctx context.Context) (any, string, error) {
		return s.fonte.Municipio(ctx, codigo)
	})
	if err != nil {
		return Resultado{}, err
	}
	return Resultado{Dados: o.dados, Meta: o.meta, Cache: o.cache}, nil
}
