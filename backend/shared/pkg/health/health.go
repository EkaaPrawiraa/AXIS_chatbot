package health

import (
	"net/http"

	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/response"
)

func Handler(w http.ResponseWriter, r *http.Request) {
	response.OK(w, map[string]string{"status": "ok"})
}
