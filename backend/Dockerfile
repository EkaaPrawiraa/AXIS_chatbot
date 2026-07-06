FROM golang:1.22-alpine AS builder

WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /out/gateway ./gateway/cmd \
    && CGO_ENABLED=0 GOOS=linux go build -o /out/auth ./services/auth/cmd \
    && CGO_ENABLED=0 GOOS=linux go build -o /out/chat ./services/chat/cmd \
    && CGO_ENABLED=0 GOOS=linux go build -o /out/memory ./services/memory/cmd \
    && CGO_ENABLED=0 GOOS=linux go build -o /out/dev ./cmd/dev

FROM alpine:3.20

RUN addgroup -S app && adduser -S app -G app

WORKDIR /app
COPY --from=builder /out/gateway /app/gateway
COPY --from=builder /out/auth /app/auth
COPY --from=builder /out/chat /app/chat
COPY --from=builder /out/memory /app/memory
COPY --from=builder /out/dev /app/dev

USER app

EXPOSE 3001 8081 8082 8083

CMD ["/app/gateway"]
