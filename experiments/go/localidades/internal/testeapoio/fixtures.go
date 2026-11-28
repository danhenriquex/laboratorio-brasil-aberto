// Package testeapoio reúne o apoio dos testes do E7: fixtures, relógio falso e IBGE simulado.
// Nenhum teste fala com host externo (Constituição IV): o IBGE é sempre um httptest.Server em loopback.
package testeapoio

import (
	"os"
	"path/filepath"
	"testing"
)

// RaizDoRepositorio sobe a partir do diretório atual até achar contracts/localidades.
func RaizDoRepositorio(t testing.TB) string {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "contracts", "localidades")); err == nil {
			return dir
		}
		pai := filepath.Dir(dir)
		if pai == dir {
			t.Fatal("não achei contracts/localidades acima do diretório atual")
		}
		dir = pai
	}
}

// Fixture lê contracts/localidades/fixtures-ibge/<nome>, as mesmas gravações usadas pelo E1 e pelo E4.
func Fixture(t testing.TB, nome string) []byte {
	t.Helper()
	conteudo, err := os.ReadFile(filepath.Join(RaizDoRepositorio(t), "contracts", "localidades", "fixtures-ibge", nome))
	if err != nil {
		t.Fatal(err)
	}
	return conteudo
}
