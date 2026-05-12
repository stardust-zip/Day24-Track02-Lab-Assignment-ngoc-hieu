import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def _auth_header(role: str) -> dict:
    """Return an Authorization header for the given role."""
    token_map = {
        "admin": "token-alice",
        "ml_engineer": "token-bob",
        "data_analyst": "token-carol",
        "intern": "token-dave",
    }
    token = token_map[role]
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# ENDPOINT 1 — GET /api/patients/raw
# =============================================================================


class TestRawPatients:
    def test_admin_can_read_raw_patients(self):
        """Admin should receive 200 with patient data."""
        response = client.get("/api/patients/raw", headers=_auth_header("admin"))
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) <= 10

    def test_data_analyst_forbidden_from_raw(self):
        """Data analyst must receive 403 on raw endpoint."""
        response = client.get("/api/patients/raw", headers=_auth_header("data_analyst"))
        assert response.status_code == 403
        assert "cannot" in response.json()["detail"].lower()

    def test_ml_engineer_forbidden_from_raw(self):
        """ML engineer must receive 403 on raw endpoint (no patient_data read)."""
        response = client.get("/api/patients/raw", headers=_auth_header("ml_engineer"))
        assert response.status_code == 403

    def test_intern_forbidden_from_raw(self):
        """Intern must receive 403 on raw endpoint."""
        response = client.get("/api/patients/raw", headers=_auth_header("intern"))
        assert response.status_code == 403

    def test_no_auth_returns_401(self):
        """Missing token should return 401."""
        response = client.get("/api/patients/raw")
        assert response.status_code == 401


# =============================================================================
# ENDPOINT 2 — GET /api/patients/anonymized
# =============================================================================


class TestAnonymizedPatients:
    def test_admin_can_read_anonymized(self):
        """Admin should receive 200 with anonymized data."""
        response = client.get("/api/patients/anonymized", headers=_auth_header("admin"))
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_ml_engineer_can_read_anonymized(self):
        """ML engineer (training_data read) should receive 200."""
        response = client.get(
            "/api/patients/anonymized", headers=_auth_header("ml_engineer")
        )
        assert response.status_code == 200

    def test_data_analyst_forbidden_from_anonymized(self):
        """Data analyst has no training_data read → 403."""
        response = client.get(
            "/api/patients/anonymized", headers=_auth_header("data_analyst")
        )
        assert response.status_code == 403

    def test_intern_forbidden_from_anonymized(self):
        """Intern has no training_data access → 403."""
        response = client.get(
            "/api/patients/anonymized", headers=_auth_header("intern")
        )
        assert response.status_code == 403

    def test_anonymized_data_no_pii(self):
        """Anonymized output should not contain original 12-digit CCCD values."""
        response = client.get("/api/patients/anonymized", headers=_auth_header("admin"))
        assert response.status_code == 200
        data = response.json()["data"]
        for record in data:
            cccd = str(record.get("cccd", ""))
            assert len(cccd) != 12, f"CCCD still 12-digit: {cccd}"


# =============================================================================
# ENDPOINT 3 — GET /api/metrics/aggregated
# =============================================================================


class TestAggregatedMetrics:
    def test_admin_can_read_metrics(self):
        """Admin should receive 200 with aggregated metrics."""
        response = client.get("/api/metrics/aggregated", headers=_auth_header("admin"))
        assert response.status_code == 200
        data = response.json()
        assert "total_patients" in data
        assert "disease_distribution" in data

    def test_data_analyst_can_read_metrics(self):
        """Data analyst (aggregated_metrics read) should receive 200."""
        response = client.get(
            "/api/metrics/aggregated", headers=_auth_header("data_analyst")
        )
        assert response.status_code == 200

    def test_ml_engineer_can_read_metrics(self):
        """ML engineer has aggregated_metrics read → 200."""
        response = client.get(
            "/api/metrics/aggregated", headers=_auth_header("ml_engineer")
        )
        assert response.status_code == 200

    def test_intern_forbidden_from_metrics(self):
        """Intern has no aggregated_metrics access → 403."""
        response = client.get("/api/metrics/aggregated", headers=_auth_header("intern"))
        assert response.status_code == 403

    def test_metrics_no_pii(self):
        """Metrics endpoint must not return any PII fields."""
        response = client.get("/api/metrics/aggregated", headers=_auth_header("admin"))
        assert response.status_code == 200
        data = response.json()
        # No 12-digit CCCD-like values should appear
        flat = str(data)
        parts = flat.split()
        for part in parts:
            if part.isdigit() and len(part) == 12:
                pytest.fail(f"Possible CCCD leaked: {part}")


# =============================================================================
# ENDPOINT 4 — DELETE /api/patients/{patient_id}
# =============================================================================


class TestDeletePatient:
    def test_admin_can_delete_patient(self):
        """Admin should be able to delete patients (200)."""
        response = client.delete("/api/patients/P00001", headers=_auth_header("admin"))
        assert response.status_code == 200
        data = response.json()
        assert "deleted_by" in data
        assert data["deleted_by"] == "alice"

    def test_data_analyst_forbidden_from_delete(self):
        """Data analyst must receive 403 on delete."""
        response = client.delete(
            "/api/patients/P00001", headers=_auth_header("data_analyst")
        )
        assert response.status_code == 403

    def test_ml_engineer_forbidden_from_delete(self):
        """ML engineer must receive 403 on delete."""
        response = client.delete(
            "/api/patients/P00001", headers=_auth_header("ml_engineer")
        )
        assert response.status_code == 403

    def test_intern_forbidden_from_delete(self):
        """Intern must receive 403 on delete."""
        response = client.delete("/api/patients/P00001", headers=_auth_header("intern"))
        assert response.status_code == 403

    def test_delete_nonexistent_returns_404(self):
        """Deleting non-existent patient returns 404."""
        response = client.delete(
            "/api/patients/INVALID_ID", headers=_auth_header("admin")
        )
        assert response.status_code == 404


# =============================================================================
# HEALTH CHECK
# =============================================================================


class TestHealthCheck:
    def test_health_returns_ok(self):
        """Health endpoint should return 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
