package operacao

import "net/http"

// Saude responde GET /health com {"status":"ok"}, sempre em application/json, qualquer que seja o Accept.
func Saude(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}
