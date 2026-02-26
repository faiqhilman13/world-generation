# Infra Notes

This repository uses Docker Compose for local development.

## Runtime dependencies

- Postgres 16
- Redis 7
- API service (`api`)
- Worker service (`worker`)
- Web service (`web`)

## Health endpoints

- API: `GET /health`
- Postgres: `pg_isready`
- Redis: `redis-cli ping`

## Environment

Use `.env.example` as the baseline and keep production secrets in a secret manager.
