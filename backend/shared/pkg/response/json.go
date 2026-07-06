package response

import (
	"encoding/json"
	"errors"
	"net/http"

	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"
)

type Body[T any] struct {
	Success bool   `json:"success"`
	Data    T      `json:"data,omitempty"`
	Error   string `json:"error,omitempty"`
	Message string `json:"message,omitempty"`
	Code    string `json:"code,omitempty"`
	Field   string `json:"field,omitempty"`
}

func JSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func Data(w http.ResponseWriter, status int, data any) {
	JSON(w, status, Body[any]{Success: true, Data: data})
}

func OK(w http.ResponseWriter, data any) {
	Data(w, http.StatusOK, data)
}

func Created(w http.ResponseWriter, data any) {
	Data(w, http.StatusCreated, data)
}

func Error(w http.ResponseWriter, status int, message string) {
	JSON(w, status, Body[any]{Success: false, Error: message, Message: message})
}

func ErrorCode(w http.ResponseWriter, status int, code string, message string, field string) {
	JSON(w, status, Body[any]{
		Success: false,
		Error:   message,
		Message: message,
		Code:    code,
		Field:   field,
	})
}

func FromError(w http.ResponseWriter, err error) {
	if err == nil {
		return
	}
	var appErr *apperrors.Error
	if errors.As(err, &appErr) {
		ErrorCode(w, statusFromAppError(appErr), appErr.Code, appErr.Error(), appErr.Field)
		return
	}
	switch {
	case errors.Is(err, apperrors.ErrNotFound):
		Error(w, http.StatusNotFound, err.Error())
	case errors.Is(err, apperrors.ErrInvalidInput):
		Error(w, http.StatusBadRequest, err.Error())
	case errors.Is(err, apperrors.ErrConflict):
		Error(w, http.StatusConflict, err.Error())
	case errors.Is(err, apperrors.ErrUnauthorized):
		Error(w, http.StatusUnauthorized, err.Error())
	case errors.Is(err, apperrors.ErrForbidden):
		Error(w, http.StatusForbidden, err.Error())
	default:
		Error(w, http.StatusInternalServerError, "internal server error")
	}
}

func statusFromAppError(err *apperrors.Error) int {
	switch {
	case errors.Is(err.Err, apperrors.ErrNotFound):
		return http.StatusNotFound
	case errors.Is(err.Err, apperrors.ErrInvalidInput):
		return http.StatusBadRequest
	case errors.Is(err.Err, apperrors.ErrConflict):
		return http.StatusConflict
	case errors.Is(err.Err, apperrors.ErrUnauthorized):
		return http.StatusUnauthorized
	case errors.Is(err.Err, apperrors.ErrForbidden):
		return http.StatusForbidden
	default:
		return http.StatusInternalServerError
	}
}
