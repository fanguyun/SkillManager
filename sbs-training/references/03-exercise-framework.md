# Exercise Framework

Source: SBS Program Bundle by Greg Nuckols

## Exercise Categories

### Main Lifts (Core Lifts)
Trained at the highest intensity in each session. Default 4 slots.

**Strength programs default**: Squat, Bench Press, Deadlift, OHP
**Hypertrophy template default**: Squat, Bench Press, Block Pulls (not Deadlift — better upper back stimulus, less low back fatigue), OHP

Main lifts can be freely customized:
- Powerlifters: Drop OHP, add 4th bench or squat variant
- Climbers: Sub bench for weighted pull-ups
- Strongmen: Sub OHP/deadlift for competition-specific variations
- General: Any barbell-based compound lift works

### Auxiliary Lifts
Close variations of main lifts — bilateral, similar ROM, barbell or barbell-like implement. Trained at lower intensity than main lifts (−10% for strength, −5% for hypertrophy).

Default 6 slots (2 squat aux, 2 bench aux, 1 deadlift aux, 1 OHP aux).

**Strength program defaults**: Front Squat, Paused Squat, Close Grip Bench, Incline Press, Sumo Deadlift, Push Press
**Hypertrophy template defaults**: Leg Press, Hack Squat, Incline Press, DB Bench, Romanian Deadlift, DB OHP

Examples of valid auxiliaries: Paused Squat, Box Squat, Squats with accommodating resistance, Close Grip Bench, Feet-Up Bench, Spoto Press, Trap Bar Deadlift, Opposite-stance Deadlift, Low Block/Rack Pulls, Push Press, Log/Axle OHP

The pre-filled auxiliaries are NOT necessarily "recommended" — they're just examples to show how the sheet works. Choose based on your preferences, weaknesses, and equipment.

### Changing Auxiliaries Mid-Program
If swapping an auxiliary:
1. Change the exercise on the Quick Setup tab
2. Do NOT change the TM on Quick Setup — instead expand the hidden TM row on the tracking sheet
3. Enter the new exercise's TM on the week you're making the switch
4. Keep each auxiliary for at least one full 7-week block

In the Program Builder, swapping is easier: just cut/paste the old lift out and the new one in.

### Upper Back Exercises
Dedicated dropdown slot in every workout across most programs. Recommended 2–3x/week minimum.

**Default dropdown options**: Barbell rows, DB rows, Chest-supported rows, T-bar rows, Pull-ups, Chin-ups, Neutral grip pull-ups, Pull-downs

You don't need to do upper back work every session — just ensure 2–3x/week. No pre-built progression; log weight/sets/reps and aim to improve over time. Previous session's numbers auto-fill as targets.

### Accessory Exercises
Everything else: single-joint, dumbbell, unilateral, machine exercises. Unfilled blue slots below "Accessories" in each workout.

**Guidance**:
- Be judicious — don't fill all slots just because they exist
- Choose accessories for specific weak points or undertrained muscle groups
- No pre-built progression — log and aim to beat previous performance
- Previous session's weight/sets/reps auto-fill as targets

To add more than 3 accessories per day, insert a new row under the last accessory row.

## Frequency Tabs

Each program spreadsheet contains multiple tabs for different training frequencies:

| Program | Available Tabs |
|---------|---------------|
| Strength (all 3 variants) | 2x, 3x, 4x, 5x, 6x |
| Hypertrophy Template | 2x, 3x, 4x, 5x, 6x |
| Linear Progression | 3x, 4x, 5x, 6x (no 2x) |
| Novice Hypertrophy | 3x, 4x, 5x (no 2x or 6x) |

Choose the tab matching how many days per week you want to train. All exercises are distributed across that many days.

### Full-Body Default
By default, all programs use full-body training for higher frequency:
- Higher frequency may be slightly better for muscle growth and strength
- Spreads training stress across more sessions (5 sets × 3 sessions > 15 sets × 1 session)
- Preserves training quality

### Lower Frequency (LF) Templates
If you prefer body-part splits or lower per-muscle frequency, use the LF variants. Same program structure, same autoregulation, same tables — but exercises are distributed so each muscle is trained fewer times per week.

The LF versions have the same tabs (2x–6x) but with different exercise distribution per day.

## Moving Exercises Around

If you don't like the default training split or exercise order:
1. **Expand** hidden TM rows (click arrows on left margin)
2. **Add** some empty rows for workspace
3. **CUT and PASTE** (NOT copy/paste) rows to rearrange
4. Arrange exercises however you like across training days

This is critical — copying instead of cutting will break the TM tracking formulas.

## Weighted Pull-Ups/Dips

When using weighted pull-ups or dips as main or auxiliary exercises, always include bodyweight + attached weight:
- You weigh 100 kg, can do a pull-up with 50 kg attached → enter 1RM as 150 kg
- This applies to both TM entry and working weight calculations

## Spreadsheet Tabs Overview

| Tab | Purpose |
|-----|---------|
| Quick Setup | Design the program (set TM, rounding, thresholds, intensity, rep targets) |
| Setup | Week-by-week view for ongoing tweaks (edit here, not Quick Setup, once started) |
| Untouched | Pulls logic directly from Setup (for building completely custom programs) |
| 2x–6x | Actual training logs where you record performance |

Blue cells are editable. White cells with formulas should not be touched.

Hidden rows between exercises contain TMs — expand by clicking arrows on the left margin, re-hide by right-clicking the row number and selecting "hide row."
