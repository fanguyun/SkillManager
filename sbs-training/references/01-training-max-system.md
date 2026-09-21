# Training Max System

Source: SBS Program Bundle by Greg Nuckols

## Core Concept

The Training Max (TM) is the engine behind all SBS programs (except Novice Hypertrophy). It is NOT your true 1RM — it's a calculated number the spreadsheet uses to determine your working weights. Your TM may drift above or below your actual 1RM depending on your strength endurance and recovery characteristics.

**Don't fixate on TM values.** They're simply numbers used to calculate appropriate training weights for the day.

## Starting Your TM

You can enter either a true 1RM or a conservative estimate. Since all programs autoregulate, the TM will self-correct within 3–4 weeks:
- If you start too low → TM increases quickly as you exceed performance targets
- If you start too high → TM decreases automatically when you fall short of targets

For the **Hypertrophy Template** specifically, Nuckols recommends starting with conservative TMs (85–90% of true max) because the program is demanding with high-rep sets.

If you don't know your 1RM, a rough estimate is fine. For weighted pull-ups/dips, include bodyweight + attached weight.

## Working Weight Formula

```
Working Weight = MROUND(TM × Week_Intensity%, Rounding_Increment)
```

- `TM`: Your current training max for that exercise
- `Week_Intensity%`: The prescribed percentage for that exercise on that week (from the intensity table)
- `Rounding_Increment`: Your smallest available weight jump
- `MROUND`: Rounds to the nearest multiple of the rounding increment

**Example**: TM = 490, Week intensity = 70%, Rounding = 2.5
→ 490 × 0.70 = 343 → MROUND(343, 2.5) = 342.5

## Rounding Increment

Set this based on your available plates:
- **Pound plates** (2.5 lb smallest): rounding = 5
- **Kilo plates** (1.25 kg smallest): rounding = 2.5
- **Mixed equipment** (different increments for different exercises): rounding = 0.1 (round manually)

The Program Builder allows per-exercise rounding increments. The standard programs use a single global rounding increment.

Note: An increase in TM doesn't always mean an increase in working weight. Small TM increases may not be enough to change the rounded working weight, but over time, working weights will increase as TM accumulates.

## Single @8 Override

Before work sets, you can optionally work up to a heavy single at RPE 8 (2 RIR). If you log this single, the spreadsheet recalculates your TM for that session:

```
New TM = Single_Weight / Single_@8_Percentage
```

- `Single_@8_Percentage`: Default 90% for all lifts (editable per exercise)
- This means a single @8 is assumed to be ~90% of your true 1RM

**Example**: Single @8 weight = 460, Single @8 percentage = 90%
→ New TM = 460 / 0.90 = 511

This updates the TM and recalculates working weights for that session immediately. It's a way to account for daily performance fluctuations.

### Customizing Single @8 Percentage

If you know your single @8 is consistently above or below 90% for specific lifts, adjust per-exercise:
- Bench press might be 93% (closer to max at RPE 8)
- Deadlift might be 87% (further from max at RPE 8)

### When to Use Singles

Nuckols' data shows that **people who regularly do overwarm singles before work sets tend to get better strength results**. Recommendation:
- Always do them for main lifts
- Doing them for all auxiliaries may be overkill
- During Block 1, you can do the single without logging it (just for neural practice)
- If you don't want the single to adjust your TM, simply don't enter the weight in the "single @8" cell

## TM Adjustment Mechanics

Each program type has its own rules for when and how much the TM changes. The general pattern:

1. **Set Threshold** (SBS Strength): TM changes based on total sets completed vs. threshold range
2. **Last Set RIR**: TM changes based on how actual RIR compares to target RIR on the last set
3. **RTF / Hypertrophy**: TM changes based on how reps on failure set compare to rep target
4. **Novice LP**: Same as Last Set RIR but with more aggressive positive adjustments

See the specific autoregulation reference files (04, 05, 06) for exact adjustment scales.

## Quick Setup vs Setup Tab

- **Quick Setup tab**: Where you design the program initially (set TM, rounding, thresholds, intensity progression)
- **Setup tab**: Week-by-week view — make ongoing tweaks here after starting the program (not in Quick Setup)

Common tweaks in the Setup tab:
- Changing TM adjustment percentages mid-program (e.g., reducing increase % after recovering from a layoff)
- Increasing set volume block-to-block
- Adjusting RIR cutoffs for specific lifts after discovering they're too high/low
