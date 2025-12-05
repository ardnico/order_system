# Dockerized deployment with nginx proxy

This ExecPlan is a living document. Keep sections such as `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` up to date per `.agent/PLANS.md`.

## Purpose / Big Picture

Containerize the FastAPI household chore app for lightweight production use and front it with an nginx reverse proxy. After completion, a novice can build images, run `docker compose up`, and access the app via nginx on port 80 with static assets served efficiently and SQLite stored on a persistent volume.

## Progress

- [x] (2025-01-06 00:10Z) Drafted initial plan.
- [x] (2025-01-06 00:25Z) Added lightweight multi-stage Dockerfile with uvicorn entrypoint and /data volume default.
- [x] (2025-01-06 00:35Z) Added docker-compose stack with nginx reverse proxy, static aliasing, and persistent volume wiring.
- [x] (2025-01-06 00:55Z) Documented Docker/nginx usage; pytest passed, docker CLI unavailable here for compose validation.

## Surprises & Discoveries

- Observation: Docker CLI is unavailable in this environment, so `docker compose config` could not be executed.
  Evidence: `bash: command not found: docker` when attempting to run compose.

## Decision Log

- Decision: Use docker compose with separate app and nginx services; keep SQLite on a named volume mounted into the app container at /data.
  Rationale: Simplifies local orchestration and persists data across restarts while allowing nginx to proxy to uvicorn.
  Date/Author: 2025-01-06 / assistant.

## Outcomes & Retrospective

Implemented containerization with a slim Python image, persistent data volume, and nginx reverse proxy configuration via docker compose. README documents compose usage and volume management. Automated tests still pass. Compose syntax validation was skipped due to missing docker tooling in the environment.

## Context and Orientation

The FastAPI app lives under `app/` with entrypoint `app.main:app`. Configuration relies on environment variables such as `DATABASE_URL` and `SESSION_SECRET`. There is no existing Dockerfile or nginx setup. The README currently covers pip-based setup only.

## Plan of Work

First, create a multi-stage `Dockerfile` using `python:3.11-slim` that installs dependencies without caches, adds a non-root user, copies the app, and runs uvicorn on `0.0.0.0:8000`. Expose port 8000 and set a default `DATABASE_URL` pointing to `/data/order_system.db` to align with the compose volume.

Next, add `docker-compose.yml` defining `app` built from the Dockerfile and `nginx` based on `nginx:alpine`. Provide an nginx config that proxies all requests to the app at `http://app:8000`, supports gzip, serves `/static` efficiently, and passes through websockets if any. Mount the nginx config and map host port 8080 or 80 to the nginx container. Attach a named volume `order_data` to `/data` in the app container.

Finally, update `README.md` with clear steps to build and run via Docker Compose, noting environment variables, default ports, and how to stop/clean up. Include a quick smoke test command (`docker compose ps` and visiting `http://localhost:8080/`).

## Concrete Steps

1. From repository root, create the Dockerfile with multi-stage build, non-root user, and uvicorn entrypoint exposing 8000.
2. Add an nginx config under `docker/nginx.conf` (or similar) with upstream pointing to `app:8000` and static cache headers.
3. Create `docker-compose.yml` defining services `app` and `nginx`, mapping host 8080:80, mounting config and data volume, and passing env defaults.
4. Update `README.md` to document docker build/run/cleanup and default ports.
5. Run `docker compose config` to validate syntax (no containers needed) and run `pytest` to ensure no regressions.
6. Record progress and outcomes in this plan.

## Validation and Acceptance

Acceptance: `docker compose up --build` starts two containers; visiting `http://localhost:8080/` renders the app via nginx. Static assets load and the app creates `/data/order_system.db` in the volume. Automated tests continue to pass via `pytest` locally. `docker compose config` should succeed without warnings.

## Idempotence and Recovery

Docker builds are repeatable; rerunning `docker compose build` overwrites images. The named volume preserves SQLite data; removing it (`docker volume rm order_system_order_data`) resets state. Config changes require `docker compose up --build` to pick up modifications.

## Artifacts and Notes

Pending execution outputs will be recorded here if relevant.

## Interfaces and Dependencies

Images: `python:3.11-slim` for the app and `nginx:alpine` for the proxy. Entrypoint uses `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Environment variable `DATABASE_URL` defaults to `sqlite:////data/order_system.db` when running via Docker.
