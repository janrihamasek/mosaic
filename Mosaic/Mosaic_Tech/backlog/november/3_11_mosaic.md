# Daily Log – 2024-11-03

- Date: 2024-11-03
- Sprint/Week: TODO
- Focus:

## Summary
- Done:
- In progress:
- Blockers:

## Decisions
- [ ] 

## Links / Artefacts
- Source: 3_11_mosaic.md

## Notes (raw import)

# Fáze 3 – Backend, migrace a DevOps
251103_devops_github_actions_ci_build
Goal: Add unified GitHub Actions workflows to automatically test and build both backend (Flask) and frontend (React) parts.  
DONE
- .github/workflows/ci.yml (line 1) defines a single workflow triggered on pushes and PRs to main.
- backend job spins up Postgres 15, configures Python 3.12 with pip cache, installs requirements.txt, runs flask db upgrade, executes pytest with coverage, and publishes mosaic_prototype/backend/coverage.xml as backend-coverage.
- frontend job sets up Node 18 with npm cache, runs npm ci, lint/tests the React app (npm run lint, npm test -- --runInBand), builds the production bundle, and uploads mosaic_prototype/frontend/build as frontend-build.
- No cross‑job dependency means both jobs run concurrently, giving fast feedback and ready-to-download artifacts for staging deploys.

251103_backend_monitoring_logging
Goal: Introduce structured logging and lightweight runtime metrics for request and error monitoring.  
DONE
Implemented structured observability across the backend.
- mosaic_prototype/backend/app.py (lines 51-214) wires structlog as the global logger, suppresses noisy Flask logs, adds per-request context binding, captures latency, user id, and status, and keeps an in-memory registry for totals/errors/status counts. Errors from validation, HTTP exceptions, and unexpected failures now log with structured context (app.py (lines 608-712)).
- New /metrics endpoint (app.py (lines 547-555)) surfaces requests_total, errors_total, avg_latency_ms, and per-status counters sourced from the in-memory registry.
- Backup scheduler logs moved to structlog (backup_manager.py (lines 18-223)) for consistent JSON output.
- Added structlog == 24.1.0 to backend dependencies (requirements.txt (line 10)).

251103_docs_logging_guide
Goal: Create concise developer documentation describing Mosaic’s structured logging and metrics system.  
DONE
Přidal jsem referenční návod docs/LOGGING.md, který shrnuje strukturu JSON logů, úrovně závažnosti, tipy pro práci s logy v Dockeru/CI, příklady filtrování přes jq/grep a význam polí v /metrics.

251103_devops_staging_postgres_ci
Goal: Add a staging environment and CI workflow that tests the full Mosaic stack against a real PostgreSQL backend.  
DONE
- Added dedicated staging configuration: .env.staging defines staging secrets/DB (.env.staging (line 1)), mosaic_prototype/database/init-mosaic.sql (line 1) now provisions the mosaic_staging database, and docker-compose.yml (line 64) / docker-compose.yml (line 109) declare mosaic_backend_staging on port 5002 plus a staging frontend on port 3001. README.md (line 42) notes the new endpoints.
- Documented structured logging and on-host metrics in docs/LOGGING.md (line 1) so developers can interpret JSON logs, filter them, and query /metrics.
- Introduced a staging CI pipeline .github/workflows/staging.yml (line 1) that spins up Postgres, runs migrations, executes pytest, smoke-tests the staging backend via /metrics, and rebuilds the React bundle with staging API settings.