"""
Regression tests covering the bugs that were fixed.

Run:  pytest -q
"""
import pytest
from fastapi.testclient import TestClient

# conftest.py has already pointed DATABASE_URL at a throwaway file.
from app.main import app


@pytest.fixture(scope="module")
def client():
    # Reset schema through SQLAlchemy rather than deleting the file, so the
    # existing connection pool stays valid.
    from app.database import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def athlete(client):
    r = client.post("/api/auth/signup", json={
        "name": "Test Athlete", "email": "athlete@test.com",
        "password": "password123", "state": "Bihar", "age": 20,
    })
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def scout(client):
    r = client.post("/api/auth/signup", json={
        "name": "Test Scout", "email": "scout@test.com",
        "password": "password123", "role": "scout",
    })
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------- health ---
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_cors_allows_local_frontend_and_rejects_unlisted_origins(client):
    allowed = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    rejected = client.options(
        "/api/health",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in rejected.headers


# ------------------------------------------------------------------ auth ---
def test_signup_works_at_all(client):
    """Regression: passlib+bcrypt raised 'password cannot be longer than
    72 bytes' on EVERY signup, so this path 500'd unconditionally."""
    r = client.post("/api/auth/signup", json={
        "name": "Fresh", "email": "fresh@test.com", "password": "password123",
    })
    assert r.status_code == 201
    assert "access_token" in r.json()


def test_long_password_does_not_crash(client):
    """Regression: a >72-byte password blew up bcrypt. Schema caps it at 128
    and the hasher truncates safely, so this must be a clean 422, not a 500."""
    r = client.post("/api/auth/signup", json={
        "name": "Long", "email": "long@test.com", "password": "x" * 300,
    })
    assert r.status_code == 422


def test_exactly_128_char_password_is_accepted(client):
    r = client.post("/api/auth/signup", json={
        "name": "Max", "email": "max@test.com", "password": "y" * 128,
    })
    assert r.status_code == 201
    r2 = client.post("/api/auth/login", data={"username": "max@test.com", "password": "y" * 128})
    assert r2.status_code == 200


def test_email_is_case_insensitive(client):
    """Regression: 'A@b.com' and 'a@b.com' could both register."""
    client.post("/api/auth/signup", json={
        "name": "Case", "email": "Case@Test.com", "password": "password123",
    })
    dup = client.post("/api/auth/signup", json={
        "name": "Case2", "email": "case@test.com", "password": "password123",
    })
    assert dup.status_code == 400
    login = client.post("/api/auth/login", data={
        "username": "CASE@TEST.COM", "password": "password123",
    })
    assert login.status_code == 200


def test_bad_credentials_rejected(client):
    r = client.post("/api/auth/login", data={"username": "athlete@test.com", "password": "nope"})
    assert r.status_code == 401


def test_malformed_token_is_401_not_500(client):
    """Regression: int(user_id) on a tampered token raised an unhandled
    ValueError, surfacing as a 500."""
    for bad in ["garbage", "a.b.c", ""]:
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad}"})
        assert r.status_code == 401


def test_me_returns_profile(client, athlete):
    r = client.get("/api/auth/me", headers=athlete)
    assert r.status_code == 200
    assert r.json()["email"] == "athlete@test.com"


# ----------------------------------------------------------------- meta ----
def test_test_types_listed(client):
    r = client.get("/api/test-types")
    assert r.status_code == 200
    keys = {t["key"] for t in r.json()}
    assert {"squat", "pushup", "plank", "vertical_jump"} <= keys


def test_stats(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    assert "total_athletes" in r.json()


# ---------------------------------------------------------------- upload ---
def test_upload_requires_auth(client):
    r = client.post("/api/assessments/upload",
                    data={"test_type": "squat"},
                    files={"file": ("a.mp4", b"x", "video/mp4")})
    assert r.status_code == 401


def test_upload_rejects_non_video(client, athlete):
    """Regression: no file-type validation at all."""
    r = client.post("/api/assessments/upload", headers=athlete,
                    data={"test_type": "squat"},
                    files={"file": ("evil.txt", b"nope", "text/plain")})
    assert r.status_code == 415


def test_upload_rejects_extensionless_filename(client, athlete):
    """Regression: filename.split('.')[-1] produced a garbage extension."""
    r = client.post("/api/assessments/upload", headers=athlete,
                    data={"test_type": "squat"},
                    files={"file": ("noext", b"data", "video/mp4")})
    assert r.status_code == 415


def test_upload_rejects_unknown_test_type(client, athlete):
    """Regression: any string was accepted, then silently scored 0."""
    r = client.post("/api/assessments/upload", headers=athlete,
                    data={"test_type": "quidditch"},
                    files={"file": ("a.mp4", b"x", "video/mp4")})
    assert r.status_code == 400


def test_upload_rejects_empty_file(client, athlete):
    r = client.post("/api/assessments/upload", headers=athlete,
                    data={"test_type": "squat"},
                    files={"file": ("a.mp4", b"", "video/mp4")})
    assert r.status_code == 400


def test_corrupt_video_marks_failed_not_stuck(client, athlete):
    """Regression: a failed analysis left the row on 'processing' forever
    with no way to know why."""
    r = client.post("/api/assessments/upload", headers=athlete,
                    data={"test_type": "squat"},
                    files={"file": ("bad.mp4", b"not really a video", "video/mp4")})
    assert r.status_code == 201
    aid = r.json()["id"]
    detail = client.get(f"/api/assessments/{aid}", headers=athlete).json()
    assert detail["status"] != "processing"
    if detail["status"] == "failed":
        assert detail["error_message"]


# ----------------------------------------------------------- permissions ---
def test_athlete_cannot_access_scout_routes(client, athlete):
    """Regression: the 'scout' role existed but had no endpoints guarding it."""
    assert client.get("/api/scouts/athletes", headers=athlete).status_code == 403
    assert client.get("/api/scouts/flagged", headers=athlete).status_code == 403


def test_scout_can_access_scout_routes(client, scout):
    assert client.get("/api/scouts/athletes", headers=scout).status_code == 200
    assert client.get("/api/scouts/flagged", headers=scout).status_code == 200


def test_cannot_view_another_users_assessment(client, athlete, scout):
    r = client.post("/api/assessments/upload", headers=athlete,
                    data={"test_type": "pushup"},
                    files={"file": ("x.mp4", b"data", "video/mp4")})
    aid = r.json()["id"]
    other = client.post("/api/auth/signup", json={
        "name": "Nosy", "email": "nosy@test.com", "password": "password123",
    }).json()
    h = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/assessments/{aid}", headers=h).status_code == 403
    # scouts may review any submission
    assert client.get(f"/api/assessments/{aid}", headers=scout).status_code == 200


# ---------------------------------------------------------- leaderboard ----
def test_leaderboard_rejects_unknown_test_type(client):
    assert client.get("/api/leaderboard", params={"test_type": "bogus"}).status_code == 400


def test_leaderboard_returns_ranks_and_dedupes(client):
    """Regression: returned one row per ATTEMPT, so a single athlete with
    many uploads filled the whole board; and had no rank field."""
    r = client.get("/api/leaderboard", params={"test_type": "squat", "limit": 20})
    assert r.status_code == 200
    rows = r.json()
    ids = [x["user_id"] for x in rows]
    assert len(ids) == len(set(ids)), "same athlete appears more than once"
    assert all(x["rank"] == i for i, x in enumerate(rows, start=1))


def test_leaderboard_states_endpoint(client):
    r = client.get("/api/leaderboard/states")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ------------------------------------------------------------------ SPA ----
def test_api_routes_do_not_shadow_spa_routes(client):
    """Regression: GET /leaderboard hit the API and returned 422 instead of
    serving the React page."""
    r = client.get("/leaderboard")
    assert r.status_code == 200


# ------------------------------------------------------------ live mode ----
def _live_payload(**over):
    base = {
        "test_type": "squat", "reps": 12, "hold_seconds": 0.0,
        "jump_height_cm": None, "duration_sec": 30.0, "bad_form_reps": 1,
        "frames_analysed": 450, "frames_with_pose": 430, "pose_coverage": 0.95,
        "scores": {"posture": 88, "balance": 92, "accuracy": 70,
                   "speed": 80, "overall_score": 82},
        "suggestions": ["Great performance!"], "unit": "reps",
    }
    base.update(over)
    return base


def test_live_submission_requires_auth(client):
    assert client.post("/api/assessments/live", json=_live_payload()).status_code == 401


def test_live_submission_succeeds(client, athlete):
    r = client.post("/api/assessments/live", headers=athlete, json=_live_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "completed"
    assert body["score"] == 12
    assert body["ai_result"]["source"] == "live_camera"


def test_local_video_result_source_is_preserved(client, athlete):
    r = client.post(
        "/api/assessments/live",
        headers=athlete,
        json=_live_payload(source="local_video"),
    )
    assert r.status_code == 201
    assert r.json()["ai_result"]["source"] == "local_video"


def test_live_rejects_unknown_test_type(client, athlete):
    r = client.post("/api/assessments/live", headers=athlete,
                    json=_live_payload(test_type="quidditch"))
    assert r.status_code == 400


def test_live_score_is_recomputed_not_trusted(client, athlete):
    """A client claiming a huge score must not have it accepted verbatim --
    the server re-derives it from the raw rep count."""
    payload = _live_payload(reps=5)
    payload["score"] = 9999          # attacker-supplied, must be ignored
    r = client.post("/api/assessments/live", headers=athlete, json=payload)
    assert r.status_code == 201
    assert r.json()["score"] == 5


def test_live_out_of_range_scores_rejected(client, athlete):
    bad = _live_payload()
    bad["scores"]["overall_score"] = 900
    assert client.post("/api/assessments/live", headers=athlete, json=bad).status_code == 422


def test_live_negative_reps_rejected(client, athlete):
    r = client.post("/api/assessments/live", headers=athlete, json=_live_payload(reps=-5))
    assert r.status_code == 422


def test_live_flags_implausible_rep_rate(client, athlete):
    """60 reps in 5 seconds is not physically plausible -> flagged."""
    r = client.post("/api/assessments/live", headers=athlete,
                    json=_live_payload(reps=60, duration_sec=5.0))
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "flagged"
    assert "implausible_rep_rate" in body["ai_result"]["cheat_flags"]


def test_live_flags_low_pose_coverage(client, athlete):
    r = client.post("/api/assessments/live", headers=athlete,
                    json=_live_payload(pose_coverage=0.2))
    assert r.json()["status"] == "flagged"


def test_live_flags_inconsistent_counts(client, athlete):
    """More bad-form reps than total reps means the client is lying."""
    r = client.post("/api/assessments/live", headers=athlete,
                    json=_live_payload(reps=3, bad_form_reps=99))
    assert "inconsistent_rep_counts" in r.json()["ai_result"]["cheat_flags"]


def test_live_hold_based_scores_in_seconds(client, athlete):
    r = client.post("/api/assessments/live", headers=athlete,
                    json=_live_payload(test_type="plank", reps=0,
                                       hold_seconds=45.5, duration_sec=45.5,
                                       unit="seconds"))
    assert r.status_code == 201
    assert r.json()["score"] == 45.5
    assert r.json()["unit"] == "seconds"


def test_live_result_appears_on_leaderboard(client, athlete):
    client.post("/api/assessments/live", headers=athlete,
                json=_live_payload(test_type="pushup", reps=40))
    rows = client.get("/api/leaderboard", params={"test_type": "pushup"}).json()
    assert any(r["score"] == 40 for r in rows)
