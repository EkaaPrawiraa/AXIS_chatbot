package errors

import "errors"

var (
	ErrNotFound     = errors.New("not found")
	ErrInvalidInput = errors.New("invalid input")
	ErrConflict     = errors.New("conflict")
	ErrUnauthorized = errors.New("unauthorized")
	ErrForbidden    = errors.New("forbidden")
)

type Error struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Field   string `json:"field,omitempty"`
	Err     error  `json:"-"`
}

func (e *Error) Error() string {
	if e.Message != "" {
		return e.Message
	}
	if e.Err != nil {
		return e.Err.Error()
	}
	return e.Code
}

func (e *Error) Unwrap() error {
	return e.Err
}

func Invalid(message string) *Error {
	return &Error{Code: "invalid_input", Message: message, Err: ErrInvalidInput}
}

func InvalidField(field, message string) *Error {
	return &Error{Code: "invalid_input", Message: message, Field: field, Err: ErrInvalidInput}
}

func NotFound(message string) *Error {
	return &Error{Code: "not_found", Message: message, Err: ErrNotFound}
}

func Conflict(message string) *Error {
	return &Error{Code: "conflict", Message: message, Err: ErrConflict}
}

func Unauthorized(message string) *Error {
	return &Error{Code: "unauthorized", Message: message, Err: ErrUnauthorized}
}

func Forbidden(message string) *Error {
	return &Error{Code: "forbidden", Message: message, Err: ErrForbidden}
}
