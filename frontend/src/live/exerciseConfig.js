/**
 * exerciseConfig.js
 * -----------------
 * Client-side mirror of app/ai/config.py (EXERCISE_CONFIG).
 *
 * Live mode runs pose estimation on the phone, so the rep thresholds have to
 * exist in JS too. This file is intentionally a 1:1 copy of the Python config
 * -- same keys, same angles -- so a rep counted live matches a rep counted
 * server-side for the same movement.
 *
 * The app fetches /api/test-types at runtime and merges the display names, so
 * the server stays the source of truth for WHICH tests exist; this file only
 * supplies the geometry the browser needs to count them.
 */

// BlazePose 33-landmark topology, same ordering as POSE_LANDMARK_NAMES
// in app/ai/pose_module.py.
export const LANDMARK = {
  NOSE: 0,
  LEFT_EYE_INNER: 1, LEFT_EYE: 2, LEFT_EYE_OUTER: 3,
  RIGHT_EYE_INNER: 4, RIGHT_EYE: 5, RIGHT_EYE_OUTER: 6,
  LEFT_EAR: 7, RIGHT_EAR: 8,
  MOUTH_LEFT: 9, MOUTH_RIGHT: 10,
  LEFT_SHOULDER: 11, RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13, RIGHT_ELBOW: 14,
  LEFT_WRIST: 15, RIGHT_WRIST: 16,
  LEFT_PINKY: 17, RIGHT_PINKY: 18,
  LEFT_INDEX: 19, RIGHT_INDEX: 20,
  LEFT_THUMB: 21, RIGHT_THUMB: 22,
  LEFT_HIP: 23, RIGHT_HIP: 24,
  LEFT_KNEE: 25, RIGHT_KNEE: 26,
  LEFT_ANKLE: 27, RIGHT_ANKLE: 28,
  LEFT_HEEL: 29, RIGHT_HEEL: 30,
  LEFT_FOOT_INDEX: 31, RIGHT_FOOT_INDEX: 32,
}

// Skeleton edges for the overlay.
export const POSE_CONNECTIONS = [
  [11, 12], [11, 23], [12, 24], [23, 24],          // torso
  [11, 13], [13, 15], [12, 14], [14, 16],          // arms
  [23, 25], [25, 27], [24, 26], [26, 28],          // legs
  [27, 29], [27, 31], [28, 30], [28, 32],          // feet
  [9, 10],                                          // mouth
]

export const EXERCISE_CONFIG = {
  pushup: {
    display_name: 'Push-ups', type: 'rep_based',
    landmarks: ['LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST'],
    up_angle: 160, down_angle: 90, unit: 'reps',
    cue_down: 'Lower your chest', cue_up: 'Push up',
  },
  squat: {
    display_name: 'Squats', type: 'rep_based',
    landmarks: ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE'],
    up_angle: 160, down_angle: 100, unit: 'reps',
    cue_down: 'Go deeper', cue_up: 'Stand tall',
  },
  situp: {
    display_name: 'Sit-ups / Crunches', type: 'rep_based',
    landmarks: ['LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE'],
    up_angle: 150, down_angle: 80, unit: 'reps',
    cue_down: 'Crunch up', cue_up: 'Lower down',
  },
  bicep_curl: {
    display_name: 'Bicep Curls', type: 'rep_based',
    landmarks: ['LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST'],
    up_angle: 150, down_angle: 40, unit: 'reps',
    cue_down: 'Curl up', cue_up: 'Extend fully',
  },
  jumping_jack: {
    display_name: 'Jumping Jacks', type: 'rep_based',
    landmarks: ['LEFT_HIP', 'LEFT_SHOULDER', 'LEFT_WRIST'],
    up_angle: 150, down_angle: 30, unit: 'reps',
    cue_down: 'Arms down', cue_up: 'Arms overhead',
  },
  lunges: {
    display_name: 'Lunges', type: 'rep_based',
    landmarks: ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE'],
    up_angle: 165, down_angle: 95, unit: 'reps',
    cue_down: 'Drop the back knee', cue_up: 'Drive up',
  },
  shoulder_press: {
    display_name: 'Shoulder Press', type: 'rep_based',
    landmarks: ['LEFT_HIP', 'LEFT_SHOULDER', 'LEFT_ELBOW'],
    up_angle: 160, down_angle: 70, unit: 'reps',
    cue_down: 'Lower to shoulders', cue_up: 'Press overhead',
  },
  tricep_dips: {
    display_name: 'Tricep Dips', type: 'rep_based',
    landmarks: ['LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST'],
    up_angle: 155, down_angle: 85, unit: 'reps',
    cue_down: 'Dip lower', cue_up: 'Extend arms',
  },
  high_knees: {
    display_name: 'High Knees', type: 'rep_based',
    landmarks: ['LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE'],
    up_angle: 150, down_angle: 80, unit: 'reps',
    cue_down: 'Knee to chest', cue_up: 'Leg down',
  },
  vertical_jump: {
    display_name: 'Vertical Jump', type: 'jump_based',
    landmarks: ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE'],
    up_angle: 165, down_angle: 110, unit: 'cm',
    cue_down: 'Crouch', cue_up: 'Jump!',
  },
  plank: {
    display_name: 'Plank Hold', type: 'hold_based',
    landmarks: ['LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_ANKLE'],
    hold_angle_min: 160, unit: 'seconds',
    cue_hold: 'Hold that line', cue_break: 'Straighten your body',
  },
  wall_sit: {
    display_name: 'Wall Sit', type: 'hold_based',
    landmarks: ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE'],
    hold_angle_min: 80, hold_angle_max: 100, unit: 'seconds',
    cue_hold: 'Hold it', cue_break: 'Knees at 90 degrees',
  },
}

export const LIVE_TESTS = Object.keys(EXERCISE_CONFIG)

/** Angle a-b-c in degrees, b is the vertex. Mirrors PoseDetector.calculate_angle. */
export function calculateAngle(a, b, c) {
  const rad = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x)
  let deg = Math.abs((rad * 180) / Math.PI)
  if (deg > 180) deg = 360 - deg
  return deg
}
