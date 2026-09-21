# Novice Programs

Source: SBS Program Bundle by Greg Nuckols
Programs: SBS Linear Progression (+ LF), SBS Novice Hypertrophy

---

## SBS Linear Progression

A program for relatively new lifters (or those returning from a layoff) who can increase strength on a week-to-week basis.

### Core Concept

- Fixed intensity each week (no block periodization)
- Fixed number of sets per exercise
- Rate RIR on the last set → TM adjusts based on performance
- Open-ended duration — run until weekly progress stalls, then transition to an intermediate program

### Default Setup

| Parameter | Value |
|-----------|-------|
| Main lifts | Squat, Bench Press, Deadlift, Push Press |
| Auxiliaries | Front Squat, Squat, Close Grip Bench, Bench Press, Deadlift, OHP |
| Back exercises | Barbell rows, DB rows, Pull-downs |
| Aux slots | 2 squat, 2 bench, 1 deadlift, 1 OHP, 3 upper back |
| Sets per exercise | 3 |
| Single @8 percentage | 90% (not recommended for novices) |
| Rounding increment | 2.5 |
| Frequency tabs | 3x, 4x, 5x, 6x (no 2x) |

### Fixed Intensities

Intensity does not change week-to-week:

| Exercise Type | %TM | Default Reps |
|--------------|-----|-------------|
| Main lifts | 87.5% | 3 per set (from rep target table at 87.5%) |
| Squat Aux 1 (Front Squat) | 82.5% | 3 per set |
| All other auxiliaries / back | 75% | 4 per set (at 75%) |

You can adjust intensities to change rep ranges. For example, changing from 87.5%/82.5%/75% to 75%/70%/65% would give sets of 4/5/6 reps instead of 3/3/4.

### RIR Targets

Default: **0 RIR** for all lifts at all intensities. This means as long as you complete the prescribed sets and reps, your TM will either stay the same or increase.

Nuckols does not recommend editing these for the LP. If you really want to, read the Last Set RIR section for how they work.

### TM Adjustment Scale (More Aggressive Than Intermediate)

| Condition | Default |
|-----------|---------|
| Failed to complete all sets | −5% |
| Completed sets, RIR below target (0) | −2% |
| RIR = 0 (last rep was a grinder) | 0% |
| RIR = 1 | +1% |
| RIR = 2 | +3% |
| RIR = 3 | +5% |
| RIR = 4 | +5% |
| RIR ≥ 5 | +5% |

These are much more aggressive than intermediate programs (max +5% vs +3%) because novices can make rapid progress.

### Rep Target Table (LP)

Used for intensities 50%–72.5%:

| %TM | 50% | 52.5% | 55% | 57.5% | 60% | 62.5% | 65% | 67.5% | 70% | 72.5% |
|-----|-----|-------|-----|-------|-----|-------|-----|-------|-----|-------|
| Reps | 20 | 18 | 16 | 15 | 14 | 13 | 12 | 11 | 10 | 9 |

The standard strength rep target table (50%–100%) is also available for higher intensities.

### Logging

Fill in "Sets completed" and "RIR on last set" columns. The TM adjusts per the scale above.

Note: A TM increase doesn't always change working weight immediately (rounding may absorb small increases), but over time weights will increase.

### Singles @8 on LP

The functionality exists but Nuckols doesn't recommend using it for novice lifters.

### Accessories

No pre-built accessory progression. Fill in weight/sets/reps and aim to improve. Previous session's data auto-fills as targets.

### Transitioning Out

When you can no longer add weight weekly (TM stalling or decreasing regularly), switch to one of the intermediate programs (Strength, Last Set RIR, RTF, or Hypertrophy).

---

## SBS Novice Hypertrophy

A program for relatively new lifters focused on muscle growth. Uses double/triple progression rather than a training max system.

### Core Concept

- **No training max system** — uses load directly
- **Double/triple progression**: sets increase → reps increase → load increases
- "Were all sets completed successfully?" — yes/no logging
- If not completed: repeat the same prescription next week
- Open-ended duration

### Default Setup

| Parameter | Value |
|-----------|-------|
| Rounding increment | Per-exercise (default 5 for weighted) |
| Frequency tabs | 3x, 4x, 5x (no 2x or 6x) |
| Exercise slots | 22 |

### Default Exercises (22 Slots)

| Category | Exercises |
|----------|-----------|
| Compound, pec-dominant (2) | Dumbbell bench press, Dumbbell incline press |
| Compound, shoulder-dominant (2) | Seated DB shoulder press, Machine shoulder press |
| Compound, upper back horizontal (2) | T-bar row, Seated cable row |
| Compound, upper back vertical (2) | Neutral grip pull-up*, Reverse grip pull-down |
| Compound, hip-dominant (2) | Romanian deadlift, Glute-ham raise |
| Compound, knee-dominant (2) | Barbell squat, Leg press |
| Hip-dominant accessory (1) | Seated hamstring curl |
| Quad-dominant accessory (1) | Split squats |
| Calves (2) | Leg press calf raises, Seated calf raises |
| Vanity lifts (6) | Preacher curls, Skullcrushers, DB rear delt raises, Trap bar shrugs, DB flyes, DB side delt raises |

*Neutral grip pull-up is a bodyweight exercise — set "bodyweight?" to "yes"

### Bodyweight Exercise Progression

Controlled by three parameters (red squares in Quick Setup):

| Parameter | Default | Purpose |
|-----------|---------|---------|
| Starting sets | 3 | Sets on first week |
| Ending sets | 5 | Max sets before rep increase |
| Reps per set increase | 1 | How many reps to add after maxing sets |

**Progression flow** (example: pull-ups starting at 5 reps):
1. 3 × 5 → complete all? → next: 4 × 5
2. 4 × 5 → complete? → next: 5 × 5
3. 5 × 5 → complete? → next: 3 × 6 (drop sets, add reps)
4. 3 × 6 → 4 × 6 → 5 × 6 → 3 × 7 → etc.

For exercises where you can do many reps (e.g., push-ups at 15+ reps), set reps per set increase to 3 (jump from 15 to 18, comparable to dips from 5 to 6).

### Weighted Exercise Progression

Controlled by seven parameters (gray squares in Quick Setup):

| Parameter | Default | Purpose |
|-----------|---------|---------|
| Starting sets | 3 | Sets on first week |
| Ending sets | 5 | Max sets before rep increase |
| Starting reps | 8 | Initial reps per set |
| Ending reps | 12 | Max reps before load increase |
| Set increase | 1 | Sets added each successful week |
| Reps per set increase | 2 | Reps added after maxing sets |
| Weight increase | 10% | Load increase after completing ending sets × ending reps |

**Progression flow** (example: bench press at 100 lb):
1. 3 × 8 @ 100 → 4 × 8 @ 100 → 5 × 8 @ 100
2. 3 × 10 @ 100 → 4 × 10 @ 100 → 5 × 10 @ 100
3. 3 × 12 @ 100 → 4 × 12 @ 100 → 5 × 12 @ 100
4. 3 × 8 @ 110 → (cycle restarts with +10% load)

This cycle takes 9 weeks per load increase with defaults. That's intentionally conservative — nearly 80% load increase per year if targets are always hit. If too slow, increase "weight increase" to 15%.

**Critical rule**: The differences between starting/ending sets and starting/ending reps MUST be evenly divisible by their respective increase values. E.g., if starting reps = 8 and ending reps = 13, reps per set increase must be 1 or 5 (not 2, 3, or 4). Violating this causes spreadsheet malfunctions.

### Simplified Variants

- **Sets only**: Set starting reps = ending reps → 3 × 8, 4 × 8, 5 × 8, then increase load
- **Reps only**: Set starting sets = ending sets → 3 × 8, 3 × 10, 3 × 12, then increase load

### Week 1 Setup

For weighted exercises: fill in starting weights on the first workout (cells say "fill"). Pick a weight that's somewhat challenging but comfortable.

For bodyweight exercises: fill in starting reps per set.

If you overshoot week 1 weights, manually enter a corrected weight for week 2. After that, the sheet handles everything.

### Logging

Type "yes" (or use dropdown) in the "were all sets completed successfully?" column if you completed all prescribed sets and reps. If not → same prescription repeats next week.

### Accessories

Three blank "Accessories" cells per day for additional exercises. Progression is entirely self-directed.
