"""Patient Access & No-Show Automation Platform — FastAPI backend.

Run from the repository root:

    uvicorn api.main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import get_store
from api.routes import appointments, clinics, dashboard, providers, risk, tasks, waitlist

app = FastAPI(
    title="Patient Access & No-Show Automation Platform API",
    description=(
        "Serves appointment risk scores, recommended staff actions, waitlist "
        "matches, provider schedules, clinic utilization, and the staff task "
        "board for the scheduling team application."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (dashboard.router, appointments.router, risk.router, waitlist.router,
          providers.router, clinics.router, tasks.router):
    app.include_router(r)


@app.on_event("startup")
def warm_store() -> None:
    store = get_store()
    print(f"Data store ready: {len(store.appointments):,} appointments, "
          f"{len(store.risk_scores):,} risk scores, {len(store.tasks):,} tasks.")


@app.get("/health", tags=["system"])
def health():
    store = get_store()
    return {
        "status": "ok",
        "mode": "csv",
        "loaded_at": store.loaded_at.isoformat(timespec="seconds"),
        "appointments": int(len(store.appointments)),
        "scheduled_upcoming": int(
            (store.appointments["appointment_status"] == "Scheduled").sum()),
        "risk_scores": int(len(store.risk_scores)),
        "open_slots": int(len(store.open_slots)),
        "waitlist_requests": int(len(store.waitlist)),
        "tasks": int(len(store.tasks)),
    }
