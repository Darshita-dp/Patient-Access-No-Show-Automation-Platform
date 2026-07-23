# Implementation Notes

Engineering decisions and how to run everything locally.

## Quick start

```bash
pip install -r requirements.txt

# 1. Data pipeline (regenerates everything deterministically, seed 42)
python etl/load_raw_data.py          # Kaggle file or synthetic fallback
python etl/clean_appointments.py
python etl/generate_synthetic_tables.py
python etl/feature_engineering.py

# 2. Model + operational outputs
python models/train_model.py
python models/score_appointments.py

# 3. Backend (http://localhost:8000/docs)
uvicorn api.main:app --reload --port 8000

# 4. Frontend (http://localhost:5173)
cd frontend && npm install && npm run dev
```

The repository ships with generated synthetic tables and scoring outputs, so
steps 3–4 work immediately after clone; steps 1–2 are only needed to
regenerate.

## Running with Docker

Reviewers who prefer a single command can use the bundled compose file:

```bash
docker compose up --build     # api :8000  +  frontend :5173
```

- **api** — `python:3.12-slim`, installs `requirements.txt`, runs
  `uvicorn api.main:app`. CSV mode is the default (`DATA_MODE=csv`), so no
  database is required. Data and models are bind-mounted from `./data` and
  `./models`, so regenerating with `etl/` or `models/train_model.py` on the
  host is visible inside the container without a rebuild.
- **frontend** — `node:20-slim`, runs the Vite dev server on `:5173` with
  `--host 0.0.0.0`. The browser (not the container) is what calls the API,
  so `VITE_API_URL=http://localhost:8000` resolves to the host's mapped
  port; no container-to-container networking is needed.
- **PostgreSQL is opt-in** via a compose profile. `docker compose --profile
  postgres up --build` adds a `postgres:16` service on `:5432`, seeded from
  `sql/`. The API still runs in CSV mode; the database is there for tools
  like Power BI Desktop, psql, or a client tool that wants the SQL model.
- Both images run as a **non-root user** and the api image ships with an
  HTTP `/health` **healthcheck**. `.dockerignore` at the repo root and in
  `frontend/` keeps `node_modules`, virtualenvs, notebooks, and raw data
  out of the build context.
- The Docker path does **not** replace the standard local setup — both are
  supported and documented in the README.

## Key decisions

**CSV-mode-first data store.** The API loads the generated CSVs into pandas
frames at startup and serves joined views identical to the SQL views. This
removes all infrastructure friction from the demo while
`etl/load_to_postgres.py` + `sql/` provide the full PostgreSQL path for BI
tools. Write endpoints (send reminder, complete task, waitlist offers) mutate
the in-memory store — an explicit simulation boundary.

**Historical vs. upcoming split.** The Kaggle dataset is a historical
extract, but an operations platform needs a live schedule. The generator
books the next 14 days of provider slot grids (62–92% fill), leaving genuine
open slots; ~5.5% of bookings are cancelled, releasing recoverable slots.
Historical rows train the model; upcoming rows get scored, actioned, tasked,
and matched.

**Leakage-safe features.** All patient/clinic/provider history features use
shifted expanding windows (prior rows only), and evaluation uses a temporal
split. This is the difference between a portfolio notebook and a model you
could actually deploy.

**Calibrated probabilities.** No class-weight rebalancing — a "72% no-show
probability" in the UI means 72%, consistent with the 19.9% base rate.
Imbalance is handled at the decision layer: percentile risk bands size the
outreach list, and reported metrics use an F1-optimal threshold chosen on
train data.

**Rules as code, not model glue.** The action engine and waitlist matcher are
plain, readable Python (`api/services/`) so a patient access manager can
audit the playbook. The waitlist score deliberately prefers likely attenders
(low risk scores positively) — the goal is filling the slot with someone who
shows up, not rewarding no-show history.

## Windows-specific notes

- If your local clone path contains `&` or spaces, `npm run build` can fail
  under cmd.exe path parsing; call vite directly:
  `node node_modules/vite/bin/vite.js build`. The canonical repo name
  (`patient-access-noshow-automation-platform`) avoids this entirely.
- Notebooks were executed with `nbclient`; re-running them requires
  `pip install nbclient ipykernel`.

## Determinism

Every generator and the model use `seed 42`. The only non-deterministic
element is "today": upcoming schedules are generated relative to the run
date, so regenerating on a different day shifts the operational window (by
design — the demo always looks current).

## Testing / verification checklist

The steps below are the **manual smoke checks** used when developing locally.
Automated coverage now backs them: **101 pytest tests** (`pytest` from the
repo root) exercise the ETL cleaning rules, risk-category thresholds, the
recommended-action engine, the waitlist-matching engine, and the FastAPI
`/health` endpoint, and a **GitHub Actions workflow** at
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs those tests
plus the frontend production build on every push and pull request.

- `python etl/*.py` in order — all exit 0, row counts printed
- `python models/train_model.py` — AUC ≈ 0.72, artifacts written
- `python models/score_appointments.py` — risk/action/task/match CSVs written
- `curl http://localhost:8000/health` — status ok with table counts
- All 21 API endpoints exercised (see README API table and `/docs`)
- `frontend`: vite build succeeds; all 8 routes render with live data and no
  console errors
- `pytest` from the repo root — 101 tests, all passing
- CI workflow green on the last push (see the CI badge in the README hero)

## Scope boundaries (what this version does not include)

Being explicit so the repository is not read as claiming more than it delivers:

- **No `.pbix` file.** The Power BI layer is a reporting-layer design: a
  seven-page specification, DAX measures, and a mock executive visual generated
  from project data. See `powerbi/README.md`.
- **No live Power Automate flow.** The outreach workflow is a specification plus
  a simulation driven by local API state transitions. No Microsoft 365 tenant,
  SharePoint list, Outlook, Teams, or SMS connector is wired up. See
  `workflows/workflow_documentation.md`.
- **No subgroup fairness audit.** Fairness considerations and limitations are
  documented in `docs/model_card.md`; the audit itself is a future enhancement.
- **Not production-validated.** The model is trained on synthetic data and is
  intended for portfolio demonstration only. Reuse under the terms of the
  MIT [`LICENSE`](../LICENSE) at the repository root.
