"""
Seed the database with demo athletes, a scout, and scored assessments so the
leaderboard and scout portal have something to show.

Usage:  python scripts/seed.py
Login for every seeded account:  password123
"""
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import models  # noqa: E402
from app.ai.config import EXERCISE_CONFIG  # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402

ATHLETES = [
    ("Aryan Sharma", "aryan@demo.in", 19, "male", "Bihar", "Patna"),
    ("Priya Nair", "priya@demo.in", 21, "female", "Kerala", "Kochi"),
    ("Rohit Kumar", "rohit@demo.in", 18, "male", "Maharashtra", "Pune"),
    ("Sneha Patel", "sneha@demo.in", 20, "female", "Gujarat", "Surat"),
    ("Vikram Singh", "vikram@demo.in", 22, "male", "Punjab", "Ludhiana"),
    ("Ananya Das", "ananya@demo.in", 17, "female", "West Bengal", "Kolkata"),
    ("Karthik Reddy", "karthik@demo.in", 23, "male", "Telangana", "Hyderabad"),
    ("Meera Joshi", "meera@demo.in", 19, "female", "Maharashtra", "Nashik"),
    ("Arjun Rao", "arjun@demo.in", 20, "male", "Karnataka", "Mysuru"),
    ("Divya Menon", "divya@demo.in", 18, "female", "Tamil Nadu", "Madurai"),
]

SEED_TESTS = ["squat", "pushup", "situp", "jumping_jack", "plank", "vertical_jump"]


def make_result(test_type: str, rng: random.Random) -> tuple[float, str, dict]:
    cfg = EXERCISE_CONFIG[test_type]
    kind = cfg["type"]
    unit = cfg.get("unit", "reps")

    if kind == "hold_based":
        score = round(rng.uniform(18, 95), 1)
        reps = 0
        duration = score
    elif kind == "jump_based":
        score = round(rng.uniform(24, 62), 1)
        reps = 1
        duration = round(rng.uniform(3, 6), 1)
    else:
        reps = rng.randint(8, 46)
        score = float(reps)
        duration = round(reps / rng.uniform(0.35, 0.7), 1)

    bad = rng.randint(0, max(1, int(reps * 0.2)))
    posture = rng.randint(58, 99)
    balance = rng.randint(55, 99)
    accuracy = rng.randint(50, 98)
    speed = rng.randint(45, 99)
    overall = round((posture + balance + accuracy + speed) / 4)

    return score, unit, {
        "test_type": test_type,
        "source": "demo_seed",
        "display_name": cfg["display_name"],
        "reps": reps,
        "hold_seconds": duration if kind == "hold_based" else 0.0,
        "jump_height_cm": score if kind == "jump_based" else None,
        "duration_sec": duration,
        "bad_form_reps": bad,
        "frames_analysed": int(duration * 15),
        "frames_with_pose": int(duration * 15 * rng.uniform(0.85, 0.99)),
        "pose_coverage": round(rng.uniform(0.85, 0.99), 3),
        "scores": {
            "posture": posture, "balance": balance,
            "accuracy": accuracy, "speed": speed,
            "overall_score": overall,
        },
        "suggestions": ["Great performance! Keep this consistency up."]
        if overall > 80
        else ["Complete the full range of motion - partial reps don't count."],
        "cheat_detected": False,
        "cheat_flags": [],
        "unit": unit,
        "score": score,
    }


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    rng = random.Random(42)
    try:
        if db.query(models.User).count() > 0:
            print("Database already has users - skipping seed.")
            print("These accounts and scores are sample data, not real assessments.")
            print("Delete sports_talent.db first if you want to reseed.")
            return 0

        db.add(models.User(
            name="Coach Verma", email="scout@demo.in",
            hashed_password=hash_password("password123"),
            role="scout", state="Delhi",
        ))

        users = []
        for name, email, age, gender, state, district in ATHLETES:
            u = models.User(
                name=name, email=email,
                hashed_password=hash_password("password123"),
                age=age, gender=gender, state=state, district=district,
                role="athlete",
            )
            db.add(u)
            users.append(u)
        db.commit()

        now = datetime.now(timezone.utc)
        count = 0
        for u in users:
            db.refresh(u)
            for test in rng.sample(SEED_TESTS, rng.randint(2, 4)):
                for _ in range(rng.randint(1, 3)):  # multiple attempts per test
                    score, unit, payload = make_result(test, rng)
                    ts = now - timedelta(days=rng.randint(0, 30), hours=rng.randint(0, 23))
                    db.add(models.Assessment(
                        user_id=u.id, test_type=test,
                        video_url=f"uploads/seed_{u.id}_{test}.mp4",
                        status="completed", score=score, unit=unit,
                        ai_result=payload, submitted_at=ts, completed_at=ts,
                    ))
                    count += 1

        # One flagged submission so the scout review queue isn't empty.
        score, unit, payload = make_result("squat", rng)
        payload["cheat_detected"] = True
        payload["cheat_flags"] = ["body_not_consistently_visible"]
        payload["pose_coverage"] = 0.34
        db.add(models.Assessment(
            user_id=users[0].id, test_type="squat",
            video_url="uploads/seed_flagged.mp4",
            status="flagged", score=score, unit=unit,
            ai_result=payload, submitted_at=now, completed_at=now,
        ))
        count += 1

        db.commit()
        print(f"Seeded {len(users)} athletes + 1 scout + {count} assessments.")
        print("All generated assessment scores are marked as sample data; no videos were analysed.")
        print("Login: aryan@demo.in / password123   (scout: scout@demo.in / password123)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
