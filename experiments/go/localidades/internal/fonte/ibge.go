// Package fonte é o cliente da API de localidades do IBGE: prazo total, classificação de falhas e
// normalização, com as regras do E1 (R1, R6 e R7) e do research do E7 (R6). Uma chamada por consulta, sem
// nova tentativa. As mensagens de erro nunca carregam o corpo devolvido pelo IBGE.
package fonte

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/dominio"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/erros"
)

const UserAgent = "laboratorio-brasil-aberto-localidades/0.1.0"

// AoMedir recebe a duração de cada consulta, inclusive das que falham. O contexto é o do pedido que
// iniciou a consulta, para o registro anotar o tempo da fonte no pedido certo.
type AoMedir func(ctx context.Context, recurso string, segundos float64)

type Cliente struct {
	base    string
	prazo   time.Duration
	aoMedir AoMedir
	http    *http.Client
}

func NovoCliente(base string, prazo time.Duration, aoMedir AoMedir) *Cliente {
	return &Cliente{
		base:    strings.TrimRight(base, "/"),
		prazo:   prazo,
		aoMedir: aoMedir,
		http: &http.Client{
			// Sem seguir redirecionamentos: um 3xx do IBGE é uma resposta inesperada.
			CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse },
		},
	}
}

// URL de um caminho relativo à base, como "estados".
func (c *Cliente) URL(caminho string) string { return c.base + "/" + caminho }

func (c *Cliente) lenta() error {
	return erros.FonteLenta("o IBGE não respondeu em %s s", strconv.FormatFloat(c.prazo.Seconds(), 'g', -1, 64))
}

// classificar separa o prazo esgotado das outras falhas de rede sem inspecionar o texto do erro.
func (c *Cliente) classificar(err error) error {
	var rede net.Error
	if errors.Is(err, context.DeadlineExceeded) || (errors.As(err, &rede) && rede.Timeout()) {
		return c.lenta()
	}
	return erros.FonteIndisponivel("não foi possível conectar ao IBGE")
}

// buscarJSON faz uma consulta com prazo total: o contexto cobre conexão, cabeçalhos e leitura do corpo.
func (c *Cliente) buscarJSON(ctx context.Context, caminho, recurso string) (any, string, error) {
	url := c.URL(caminho)
	ctx, cancelar := context.WithTimeout(ctx, c.prazo)
	defer cancelar()

	inicio := time.Now()
	status, corpo, err := c.consultar(ctx, url)
	if c.aoMedir != nil {
		c.aoMedir(ctx, recurso, time.Since(inicio).Seconds())
	}
	if err != nil {
		return nil, url, c.classificar(err)
	}
	if status >= 500 || status == http.StatusTooManyRequests {
		return nil, url, erros.FonteIndisponivel("o IBGE respondeu com status %d", status)
	}
	if status != http.StatusOK {
		return nil, url, erros.RespostaInesperadaDaFonte("o IBGE respondeu com status %d", status)
	}
	decodificador := json.NewDecoder(bytes.NewReader(corpo))
	decodificador.UseNumber()
	var dados any
	if err := decodificador.Decode(&dados); err != nil || decodificador.More() {
		return nil, url, erros.RespostaInesperadaDaFonte("o IBGE respondeu um conteúdo que não é JSON")
	}
	return dados, url, nil
}

func (c *Cliente) consultar(ctx context.Context, url string) (int, []byte, error) {
	pedido, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return 0, nil, err
	}
	pedido.Header.Set("User-Agent", UserAgent)
	pedido.Header.Set("Accept", "application/json")
	resposta, err := c.http.Do(pedido)
	if err != nil {
		return 0, nil, err
	}
	defer resposta.Body.Close()
	corpo, err := io.ReadAll(resposta.Body)
	if err != nil {
		return 0, nil, err
	}
	return resposta.StatusCode, corpo, nil
}

// Estados devolve as 27 UFs, na ordem em que o IBGE mandou.
func (c *Cliente) Estados(ctx context.Context) ([]dominio.UF, string, error) {
	dados, url, err := c.buscarJSON(ctx, "estados", "estados")
	if err != nil {
		return nil, url, err
	}
	itens, err := lista(dados)
	if err == nil && len(itens) == 0 {
		err = forma("lista de UFs vazia")
	}
	var ufs []dominio.UF
	for _, item := range itens {
		if err != nil {
			break
		}
		var uf dominio.UF
		uf, err = lerUF(item)
		ufs = append(ufs, uf)
	}
	if err != nil {
		return nil, url, erros.RespostaInesperadaDaFonte("a lista de UFs do IBGE veio fora do formato esperado (%s)", err)
	}
	return ufs, url, nil
}

// MunicipiosDaUF devolve os municípios de uma UF existente.
func (c *Cliente) MunicipiosDaUF(ctx context.Context, codigoUF string) ([]dominio.MunicipioResumido, string, error) {
	dados, url, err := c.buscarJSON(ctx, "estados/"+codigoUF+"/municipios", "municipios_da_uf")
	if err != nil {
		return nil, url, err
	}
	itens, err := lista(dados)
	if err == nil && len(itens) == 0 {
		err = forma("lista vazia para uma UF existente")
	}
	var municipios []dominio.MunicipioResumido
	for _, item := range itens {
		if err != nil {
			break
		}
		var m dominio.MunicipioResumido
		m, err = lerMunicipioResumido(item)
		municipios = append(municipios, m)
	}
	if err != nil {
		return nil, url, erros.RespostaInesperadaDaFonte(
			"a lista de municípios da UF %s veio fora do formato esperado (%s)", codigoUF, err)
	}
	return municipios, url, nil
}

// Municipio devolve um município pelo código. "Não encontrado" no IBGE é uma lista vazia.
func (c *Cliente) Municipio(ctx context.Context, codigo string) (dominio.Municipio, string, error) {
	dados, url, err := c.buscarJSON(ctx, "municipios/"+codigo, "municipio")
	if err != nil {
		return dominio.Municipio{}, url, err
	}
	if l, ok := dados.([]any); ok && len(l) == 0 {
		return dominio.Municipio{}, url, erros.NaoEncontrado("não existe município com o código %s", codigo)
	}
	if l, ok := dados.([]any); ok {
		if len(l) != 1 {
			return dominio.Municipio{}, url, erros.RespostaInesperadaDaFonte(
				"o município %s veio fora do formato esperado (esperava um único município)", codigo)
		}
		dados = l[0]
	}
	m, err := lerMunicipio(dados)
	if err != nil {
		return dominio.Municipio{}, url, erros.RespostaInesperadaDaFonte("o município %s veio fora do formato esperado (%s)", codigo, err)
	}
	if m.Codigo != codigo {
		return dominio.Municipio{}, url, erros.RespostaInesperadaDaFonte("o IBGE devolveu outro município ao pedir %s", codigo)
	}
	return m, url, nil
}

// --- leitura da forma descrita no data-model ---

type formaInesperada string

func (f formaInesperada) Error() string { return string(f) }

func forma(formato string, args ...any) error { return formaInesperada(fmt.Sprintf(formato, args...)) }

// Regras do data-model para as siglas expostas (T049 do E1).
var (
	reSiglaUF     = regexp.MustCompile(`^[A-Z]{2}$`)
	reSiglaRegiao = regexp.MustCompile(`^[A-Z]{1,2}$`)
)

func lista(dados any) ([]any, error) {
	l, ok := dados.([]any)
	if !ok {
		return nil, forma("esperava uma lista")
	}
	return l, nil
}

func campo(objeto any, chave string) (any, error) {
	m, ok := objeto.(map[string]any)
	if !ok {
		return nil, forma("campo obrigatório ausente: %s", chave)
	}
	valor, ok := m[chave]
	if !ok || valor == nil {
		return nil, forma("campo obrigatório ausente: %s", chave)
	}
	return valor, nil
}

// codigo exige a quantidade exata de dígitos: completar com zeros inventaria um código (T048 do E1).
func codigo(objeto any, digitos int) (string, error) {
	valor, err := campo(objeto, "id")
	if err != nil {
		return "", err
	}
	var texto string
	switch v := valor.(type) {
	case json.Number:
		texto = v.String()
	case string:
		texto = strings.TrimSpace(v)
	default:
		return "", forma("id com tipo inesperado")
	}
	if len(texto) != digitos || strings.Trim(texto, "0123456789") != "" {
		return "", forma("id fora do formato de %d dígitos", digitos)
	}
	return texto, nil
}

func texto(objeto any, chave string) (string, error) {
	valor, err := campo(objeto, chave)
	if err != nil {
		return "", err
	}
	s, ok := valor.(string)
	if !ok || strings.TrimSpace(s) == "" {
		return "", forma("campo %s vazio ou não textual", chave)
	}
	return s, nil
}

func sigla(objeto any, formato *regexp.Regexp) (string, error) {
	valor, err := texto(objeto, "sigla")
	if err != nil {
		return "", err
	}
	if !formato.MatchString(valor) {
		return "", forma("sigla fora do formato esperado")
	}
	return valor, nil
}

// leitor acumula o primeiro erro, para a leitura dos campos ficar linear.
type leitor struct{ err error }

func (l *leitor) codigo(objeto any, digitos int) string {
	if l.err != nil {
		return ""
	}
	v, err := codigo(objeto, digitos)
	l.err = err
	return v
}

func (l *leitor) texto(objeto any, chave string) string {
	if l.err != nil {
		return ""
	}
	v, err := texto(objeto, chave)
	l.err = err
	return v
}

func (l *leitor) sigla(objeto any, formato *regexp.Regexp) string {
	if l.err != nil {
		return ""
	}
	v, err := sigla(objeto, formato)
	l.err = err
	return v
}

func (l *leitor) campo(objeto any, chave string) any {
	if l.err != nil {
		return nil
	}
	v, err := campo(objeto, chave)
	l.err = err
	return v
}

func lerUF(objeto any) (dominio.UF, error) {
	var l leitor
	regiao := l.campo(objeto, "regiao")
	uf := dominio.UF{
		Codigo: l.codigo(objeto, 2),
		Sigla:  l.sigla(objeto, reSiglaUF),
		Nome:   l.texto(objeto, "nome"),
	}
	uf.Regiao = dominio.Regiao{
		Codigo: l.codigo(regiao, 1),
		Sigla:  l.sigla(regiao, reSiglaRegiao),
		Nome:   l.texto(regiao, "nome"),
	}
	return uf, l.err
}

func lerMunicipioResumido(objeto any) (dominio.MunicipioResumido, error) {
	var l leitor
	m := dominio.MunicipioResumido{Codigo: l.codigo(objeto, 7), Nome: l.texto(objeto, "nome")}
	return m, l.err
}

func lerMunicipio(objeto any) (dominio.Municipio, error) {
	var l leitor
	imediata := l.campo(objeto, "regiao-imediata")
	intermediaria := l.campo(imediata, "regiao-intermediaria")
	uf := l.campo(intermediaria, "UF")
	m := dominio.Municipio{
		Codigo: l.codigo(objeto, 7),
		Nome:   l.texto(objeto, "nome"),
		UF: dominio.UFResumida{
			Codigo: l.codigo(uf, 2),
			Sigla:  l.sigla(uf, reSiglaUF),
			Nome:   l.texto(uf, "nome"),
		},
		RegiaoImediata:      dominio.RegiaoImediata{Codigo: l.codigo(imediata, 6), Nome: l.texto(imediata, "nome")},
		RegiaoIntermediaria: dominio.RegiaoIntermediaria{Codigo: l.codigo(intermediaria, 4), Nome: l.texto(intermediaria, "nome")},
	}
	return m, l.err
}
