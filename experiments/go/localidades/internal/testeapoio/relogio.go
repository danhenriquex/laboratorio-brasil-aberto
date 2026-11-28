package testeapoio

import (
	"sync"
	"time"
)

// Relogio é um relógio falso: o instante de parede começa em 2026-11-26T12:00:00.123Z e a fonte monotônica
// em zero, e os dois só andam com Avancar. Assim os testes de validade não esperam de verdade.
type Relogio struct {
	mu         sync.Mutex
	agora      time.Time
	monotonico time.Duration
}

func NovoRelogio() *Relogio {
	return &Relogio{agora: time.Date(2026, 11, 26, 12, 0, 0, 123_000_000, time.UTC)}
}

func (r *Relogio) Agora() time.Time {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.agora
}

func (r *Relogio) Monotonico() time.Duration {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.monotonico
}

func (r *Relogio) Avancar(d time.Duration) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.agora = r.agora.Add(d)
	r.monotonico += d
}
