"""FastAPI health endpoint.

/health is what the frontend and any deployment probe rely on to know the API
came up with its data loaded — so it must report real table counts, not just
return 200.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_health_reports_ok_status(self, client):
        body = client.get("/health").json()

        assert body["status"] == "ok"

    def test_health_reports_the_data_mode(self, client):
        body = client.get("/health").json()

        assert body["mode"] == "csv"

    def test_health_reports_a_loaded_timestamp(self, client):
        body = client.get("/health").json()

        assert body["loaded_at"]

    def test_health_reports_non_empty_table_counts(self, client):
        # A 200 with zero rows would mean the store failed to load — the exact
        # failure this probe exists to catch.
        body = client.get("/health").json()

        for key in ("appointments", "risk_scores", "open_slots",
                    "waitlist_requests", "tasks"):
            assert isinstance(body[key], int), f"{key} should be an int"
            assert body[key] > 0, f"{key} should have loaded rows"

    def test_scheduled_upcoming_is_a_subset_of_all_appointments(self, client):
        body = client.get("/health").json()

        assert 0 < body["scheduled_upcoming"] <= body["appointments"]

    def test_every_scheduled_appointment_is_scored(self, client):
        # The queue would silently drop appointments if scoring lagged intake.
        body = client.get("/health").json()

        assert body["risk_scores"] == body["scheduled_upcoming"]


class TestApiSurface:
    def test_openapi_schema_is_served(self, client):
        response = client.get("/openapi.json")

        assert response.status_code == 200
        assert response.json()["info"]["title"]

    def test_core_operational_routes_are_registered(self, client):
        paths = client.get("/openapi.json").json()["paths"]

        for route in ("/health", "/appointments", "/risk/high", "/waitlist",
                      "/providers", "/clinics/utilization", "/tasks"):
            assert route in paths, f"{route} is missing from the API"

    def test_unknown_route_returns_404(self, client):
        assert client.get("/not-a-real-route").status_code == 404
