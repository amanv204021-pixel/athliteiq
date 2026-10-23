"""
config.py
---------
Configuration for every supported exercise/test: which body landmarks to
track, and which angles count as the 'up' / 'down' (or 'hold') position.

TO ADD A NEW SPORT/TEST: add one entry to EXERCISE_CONFIG below. No other
file needs to change -- the whole analysis pipeline is driven by this dict.
This is "config-driven design".

Landmark names must match the BlazePose 33-point topology
(see POSE_LANDMARK_NAMES in pose_module.py), e.g. LEFT_SHOULDER,
LEFT_ELBOW, LEFT_WRIST, LEFT_HIP, LEFT_KNEE, LEFT_ANKLE.

Field reference
---------------
type            : "rep_based" | "hold_based"
landmarks       : (a, b, c) -- b is the vertex whose angle is measured
up_angle        : angle above which we are in the 'up' state
down_angle      : angle below which we are in the 'down' state (rep counts here)
hold_angle_min  : hold_based -- minimum acceptable angle
hold_angle_max  : hold_based -- maximum acceptable angle (optional)
unit            : what the primary score is measured in
higher_is_better: ranking direction, used by the leaderboard
"""

EXERCISE_CONFIG: dict[str, dict] = {

    # ---------------- REP-BASED EXERCISES ----------------
    # The tracked angle oscillates between an 'up' and a 'down' position;
    # each up -> down transition counts one rep.

    "pushup": {
        "display_name": "Push-ups",
        "type": "rep_based",
        "landmarks": ("LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST"),
        "up_angle": 160,      # arm straight -> 'up'
        "down_angle": 90,     # arm bent -> 'down' (rep counts here)
        "unit": "reps",
        "higher_is_better": True,
    },

    "squat": {
        "display_name": "Squats",
        "type": "rep_based",
        "landmarks": ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"),
        "up_angle": 160,      # standing
        "down_angle": 100,    # seated depth
        "unit": "reps",
        "higher_is_better": True,
    },

    "situp": {
        "display_name": "Sit-ups / Crunches",
        "type": "rep_based",
        "landmarks": ("LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE"),
        "up_angle": 150,      # lying flat
        "down_angle": 80,     # crunched up
        "unit": "reps",
        "higher_is_better": True,
    },

    "bicep_curl": {
        "display_name": "Bicep Curls",
        "type": "rep_based",
        "landmarks": ("LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST"),
        "up_angle": 150,      # arm extended
        "down_angle": 40,     # arm curled
        "unit": "reps",
        "higher_is_better": True,
    },

    "jumping_jack": {
        "display_name": "Jumping Jacks",
        "type": "rep_based",
        "landmarks": ("LEFT_HIP", "LEFT_SHOULDER", "LEFT_WRIST"),
        "up_angle": 150,      # arms overhead
        "down_angle": 30,     # arms at sides
        "unit": "reps",
        "higher_is_better": True,
    },

    "lunges": {
        "display_name": "Lunges",
        "type": "rep_based",
        "landmarks": ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"),
        "up_angle": 165,      # standing, front leg straight
        "down_angle": 95,     # lunge, knee ~90
        "unit": "reps",
        "higher_is_better": True,
    },

    "shoulder_press": {
        "display_name": "Shoulder Press",
        "type": "rep_based",
        "landmarks": ("LEFT_HIP", "LEFT_SHOULDER", "LEFT_ELBOW"),
        "up_angle": 160,      # arm fully overhead
        "down_angle": 70,     # arm at shoulder level
        "unit": "reps",
        "higher_is_better": True,
    },

    "tricep_dips": {
        "display_name": "Tricep Dips",
        "type": "rep_based",
        "landmarks": ("LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST"),
        "up_angle": 155,      # arms extended
        "down_angle": 85,     # arms bent
        "unit": "reps",
        "higher_is_better": True,
    },

    "high_knees": {
        "display_name": "High Knees",
        "type": "rep_based",
        "landmarks": ("LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE"),
        "up_angle": 150,      # leg down, hip open
        "down_angle": 80,     # knee raised to chest
        "unit": "reps",
        "higher_is_better": True,
    },

    "vertical_jump": {
        "display_name": "Vertical Jump",
        "type": "jump_based",
        "landmarks": ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"),
        # Jump height is measured from hip displacement across frames rather
        # than a joint angle, so thresholds here only gate the crouch phase.
        "up_angle": 165,
        "down_angle": 110,
        "unit": "cm",
        "higher_is_better": True,
    },

    # ---------------- HOLD-BASED EXERCISES ----------------
    # No reps -- we track how long a correct position is sustained.

    "plank": {
        "display_name": "Plank Hold",
        "type": "hold_based",
        "landmarks": ("LEFT_SHOULDER", "LEFT_HIP", "LEFT_ANKLE"),
        "hold_angle_min": 160,   # body should form a straight line (~180 ideal)
        "unit": "seconds",
        "higher_is_better": True,
    },

    "wall_sit": {
        "display_name": "Wall Sit",
        "type": "hold_based",
        "landmarks": ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"),
        "hold_angle_min": 80,    # knee bent ~90
        "hold_angle_max": 100,   # outside this range = form break
        "unit": "seconds",
        "higher_is_better": True,
    },
}


def get_exercise(test_type: str) -> dict:
    """Look up one exercise config, raising a clear error if unknown."""
    try:
        return EXERCISE_CONFIG[test_type]
    except KeyError as exc:
        valid = ", ".join(sorted(EXERCISE_CONFIG))
        raise KeyError(f"Unknown test_type '{test_type}'. Valid options: {valid}") from exc


def is_higher_better(test_type: str) -> bool:
    """
    Ranking direction for the leaderboard.
    Defaults to True for unknown types so ordering stays predictable.
    """
    cfg = EXERCISE_CONFIG.get(test_type)
    return True if cfg is None else cfg.get("higher_is_better", True)


SUPPORTED_TESTS: list[str] = sorted(EXERCISE_CONFIG)
