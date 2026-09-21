# Program Builder

Source: SBS Program Bundle by Greg Nuckols
Program: SBS Program Builder

## Overview

The Program Builder is the definitive version of the SBS program concept. Its key strength is **mix-and-match** — you can combine different progression schemes for different exercises within a single program.

This guide assumes familiarity with the other SBS progression schemes (Set Threshold, Last Set RIR, RTF, Hypertrophy RTF, LP). Read those reference files first if needed.

## 7 Available Progression Schemes

The Program Builder offers 7 progressions. The first 7 come from the other SBS programs; the last 5 are accessory-specific.

### TM-Based Progressions (from other programs)

1. **Set Threshold** (blue cells) — from SBS Strength Program. See `04-autoregulation-set-threshold.md`.
2. **Last Set RIR** (combined with LP logic) — from SBS Strength Last Set RIR / LP. See `05-autoregulation-last-set-rir.md`. Toggle "LP preset" to use Linear Progression defaults.
3. **RTF** (green cells) — from SBS Strength RTF. Toggle "Hypertrophy preset" to use Hypertrophy Template defaults. See `06-autoregulation-rtf.md`.

### 5 Accessory Progressions

These do NOT use a training max. Progression is based purely on performance.

#### 4. Rep Increase (Light Burgundy Cells)

Same as Novice Hypertrophy bodyweight progression:
- Sets increase from starting to ending sets
- Then reps per set increase
- Cycle repeats

Fill in week 1 reps per set. The sheet handles the rest.

#### 5. Set Increase Then Rep Increase (Gray Cells)

Same as Novice Hypertrophy weighted progression:
- Sets increase → reps increase → load increases
- Three-step cycle: 3×8 → 4×8 → 5×8 → 3×10 → ... → 5×12 → 3×8 @ higher weight

Fill in week 1 weight. Parameters: starting sets, ending sets, starting reps, ending reps, set increase, reps per set increase, weight increase (default 10%).

#### 6. Classic Overload (Teal Cells)

Simple set/rep goal with percentage-based load increase:
- Assign a set and rep goal (default: 3 × 10)
- Complete all sets? → Load increases by % (default 3%) or minimum increment (whichever is larger)
- Fall short? → Load stays the same

Log: number of sets completed successfully.

**Example**: DB bench 80 lb, goal 3 × 10. Complete 2 × 10 + 1 × 8 → log 2 sets successful → load unchanged. Next week, complete 3 × 10 → log 3 sets → load increases to 82.5 lb (3% of 80 = 2.4, minimum increment = 2.5).

#### 7. Fixed Number of Reps (Yellow Cells)

Total rep target across multiple sets to failure:
- Assign total reps and number of sets (default: 40 reps over 3 sets)
- Do N sets to failure, count total reps
- Hit target? → Load increases by 3% or minimum increment
- Miss? → Load unchanged

**Example**: Triceps pushdowns, 3 sets to failure with 50 lb. Get 15 + 14 + 12 = 41 reps ≥ 40 → load increases.

#### 8. Set-by-Set / Reverse Pyramid (Peach Cells)

Independent progression per set:
- Assign rep targets for each set individually
- Load progresses per-set — if you hit targets on sets 1 and 2 but not set 3, only sets 1 and 2 get heavier

**Default**: Reverse pyramid (higher reps on earlier sets, fewer reps on later/heavier sets).

**Creative uses**: Build pyramids by combining two adjacent exercise entries. For example, make "lift 17" and "lift 18" both triceps extensions: sets 1-3 ascending, sets 4-5 (from "lift 18") descending.

## Quick Setup Structure

### Exercise Entries (C5–C44)

Up to 40 exercises. For each exercise:
- **Auxiliary toggle** (A5–A44): "yes" if it should use auxiliary intensity/rep tables
- **Rounding increment** (B5–B44): Per-exercise (unlike other programs)
- **Training max** (D5–D44): For TM-based progressions only
- **Single @8 %** (E5–E44): For TM-based progressions only
- **Progression parameters** (F2–AZ44): Only edit the columns for the progression you're using for that exercise

### Tables in Quick Setup

| Rows | Content | Used By |
|------|---------|---------|
| 46–132 | Reps at a given percent + RIR cutoffs | Set Threshold progression |
| 136–221 | Rep targets + Last Set RIR targets | Last Set RIR / LP progressions |
| 225–310 | Normal set rep targets + Last set rep targets | RTF / Hypertrophy progressions |
| 312–353 | Weekly intensity per exercise | All TM-based progressions |
| 356–397 | Deload toggles per exercise per week | All TM-based progressions |
| 399–403 | Deload details | All TM-based progressions |

### Presets and Toggles

- **LP preset** (A138–A177): Toggle "yes" to use LP intensity/RIR defaults for a lift
- **Hypertrophy preset** (A227–A266): Toggle "yes" to use Hypertrophy Template rep/intensity defaults
- **Auxiliary toggle** (A5–A44): Auto-applies auxiliary intensity tables

These toggles auto-populate intensity and rep target cells. The blacked-out cells below preset rows are auto-repeated — don't edit them.

## Deload Configuration

### Deload Toggles (Rows 356–397)

Per-exercise, per-week toggles. Default: weeks 7, 14, 21 for all TM-based exercises. Customize freely.

Deload logic does NOT apply to exercises using accessory progressions.

### Deload Details (B399–C403)

| Parameter | Default |
|-----------|---------|
| Reps per set | Customizable |
| Sets | Customizable |
| Intensity | Customizable |
| TM change | 0% (no change) |

You can configure deloads to:
- High intensity / low volume: 80–85%, 2–4 sets of 1–2 reps
- Low intensity / moderate volume: standard approach
- TM decrease: −3% to ease into next block
- TM increase: +1–2% if progressing quickly

## Program Tab Assembly

The Program tab contains all exercise rows starting at row 150. You build your program by **cutting and pasting** (NOT copy/paste) rows to the top of the sheet.

### Assembly Workflow

1. Find the rows for your first exercise in the color matching your chosen progression
2. **Cut** those rows (include the hidden TM row)
3. **Paste** at the top of the Program tab
4. Repeat for each exercise
5. Add "Day 1", "Day 2", etc. headers for organization
6. Hide TM rows if desired
7. Fill in week 1 weights for accessory progressions

### Color Coding

| Color | Progression |
|-------|-------------|
| Blue | Set Threshold |
| (combined) | Last Set RIR / LP |
| Green | RTF / Hypertrophy RTF |
| Light Burgundy | Rep Increase |
| Gray | Set Increase Then Rep Increase |
| Teal | Classic Overload |
| Yellow | Fixed Number of Reps |
| Peach | Set-by-Set / Reverse Pyramid |

### Rules

- Cells with existing numbers contain formulas — don't edit them
- Gray cells are for user input (week 1 weights, etc.)
- If you mess up the Program tab, duplicate the Untouched tab and start over
- The sheet works on mobile but setup is much easier on desktop

## Swapping Exercises or Progressions

Easier than in the standard programs:
1. Cut/paste the old exercise/progression out
2. Cut/paste the new one in
3. Update training maxes if applicable

No need to go back to Quick Setup for auxiliary swaps.

## Example Use Case

"I like RTF for most lifts, but deadlifts burn me out with AMRAP sets."

→ Use RTF progression (green) for squat, bench, OHP
→ Use Set Threshold progression (blue) for deadlift
→ Use Classic Overload (teal) for accessories
→ Use Reverse Pyramid (peach) for arm work
