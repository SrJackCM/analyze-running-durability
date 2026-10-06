---
name: analyze-running-durability
description: Analyze a runner's durability across repeated long runs by combining heart-rate–output decoupling, RPE, fueling, weather, terrain, symptom sequence, and 24–48 hour recovery. Use when planning a four-week durability field test; reviewing long-run, marathon, trail, or ultra data; comparing three or more similar sessions; investigating late-run fade; or deciding whether the next training emphasis should be volume, strength, fueling and gut training, heat adaptation, recovery, or pacing. Do not use a single decoupling percentage as a diagnosis or universal pass/fail threshold.
---

# Analyze Running Durability

Treat durability as the timing and magnitude of performance or physiological deterioration during prolonged exercise. Separate fresh-state ability from the ability to retain it under accumulated load.

## Choose the operating mode

- **Design the field test:** Build a four-week plan with three comparable long runs and a recording template. Read `references/data-schema.md`.
- **Normalize supplied data:** Convert pace to speed, gels to carbohydrate grams, drinks to milliliters, and totals to hourly rates. For CSV data, use `scripts/summarize_durability.py` when its schema fits. For Garmin FIT files, use `scripts/fit_to_summary.py` to extract first-/second-half heart rate, speed (or power), and mid-run temperature directly from the raw records.
- **Analyze one session:** Describe what changed first and what followed. Do not infer a stable limitation from one run.
- **Compare repeated sessions:** Read `references/interpretation.md`; assess comparability before interpreting trends.
- **Analyze trail or ultra data:** Use comparable course segments rather than whole-run pace–heart-rate decoupling when grade, surface, altitude, stops, or hiking vary substantially.

## Establish context

Collect only context that changes interpretation:

- event type, goal duration, terrain, and expected environmental conditions;
- recent 5K, 10K, half-marathon, or marathon ability when available;
- typical weekly volume, longest recent run, strength work, and training age;
- relevant illness, injury, medication, sleep disruption, altitude exposure, or heat acclimation;
- whether the goal is diagnosis of a past fade or selection of the next training emphasis.

Do not delay analysis for optional details. Mark missing information and lower confidence instead.

## Design a four-week field test

Schedule three long runs whose route, intended intensity, duration, start time, pre-run meal, footwear, and fueling plan are as similar as practical. Do not force identical sessions when that conflicts with safe progression or the athlete's current plan.

For each run, record:

1. First- and second-half average heart rate plus speed or running power, and RPE for each half.
2. Total carbohydrate grams and fluid milliliters; normalize both per hour.
3. Temperature, humidity, elevation gain, route, surface, stops, and technical difficulty.
4. The first meaningful change in the second half: heart rate, breathing, cadence or form, leg pain or weakness, gastrointestinal tolerance, attention, motivation, or another athlete-reported signal. Record its approximate elapsed time.
5. Recovery at 24 and 48 hours: soreness, fatigue, sleep, resting heart rate or HRV when normally used, and readiness to complete planned training.

Avoid deliberately withholding carbohydrate, fluid, or heat protection merely to create contrast. Use naturally occurring or safely planned differences.

## Normalize the measurements

Use speed rather than pace in efficiency calculations:

`speed_km_h = 60 / pace_min_per_km`

For each half:

`efficiency_factor = speed_km_h / average_heart_rate`

or, when running power is reasonably comparable:

`efficiency_factor = average_power_w / average_heart_rate`

Calculate simplified decoupling as:

`decoupling_pct = (EF_first - EF_second) / EF_first * 100`

Positive values indicate lower output per heartbeat in the second half. Negative values indicate improvement, which may reflect warm-up, conservative pacing, terrain, sensor error, or genuine negative splitting; inspect the session before interpreting it.

Never mix speed-based and power-based efficiency factors in the same trend. Avoid power comparisons across device changes or materially different algorithms.

## Judge comparability before causality

Rate cross-session comparability:

- **High:** similar duration, route or grade profile, intensity, weather, stops, and measurement method.
- **Moderate:** one meaningful difference that can be described and considered.
- **Low:** several large differences, substantial trail variability, sensor gaps, illness, race effort, or unmatched durations.

With low comparability, describe each run and generate hypotheses; do not rank training investments confidently.

Do not treat 5% decoupling as a universal physiological boundary. Prioritize:

- when deterioration begins;
- which signal changes first;
- whether onset moves later across comparable runs;
- whether adequate fueling, cooler conditions, or more rational pacing changes the pattern;
- whether the athlete can recover within 24–48 hours without disrupting subsequent training.

## Build an evidence chain

For every hypothesis, show:

1. **Observed data:** the exact pattern in the runs.
2. **Plausible interpretation:** the mechanism or training limitation consistent with it.
3. **Competing explanations:** weather, route, sensor error, pacing, illness, sleep, or fueling differences.
4. **Confidence:** high, moderate, or low, based on repetition and comparability.
5. **Next discriminating test:** the smallest safe change that would make the explanations easier to separate.

Do not label normal late-run fatigue as a disorder. Do not turn wearable HRV, heart rate, or running-power values into a medical diagnosis.

## Select the next training emphasis

Recommend one primary investment and, when justified, one secondary investment. Choose among:

- aerobic volume or longer effective duration;
- maximum strength, plyometrics, or terrain-specific muscular endurance;
- fueling and gastrointestinal training;
- heat adaptation and hydration planning;
- pacing and race-intensity control;
- recovery, load reduction, or sleep support;
- further measurement before changing training.

Tie the recommendation to the athlete's event. A road marathon may prioritize steady output retention; trail and ultra analysis must also account for downhill damage, hiking transitions, gastrointestinal durability, cognition, feet, and aid-station execution.

Avoid recommending more volume by default. If deterioration follows an over-fast opening, poor fueling, high heat strain, or damaging descents, simply extending the run may reproduce the problem at higher cost.

## Produce the report

Return the following sections:

1. **Bottom line:** one sentence naming the most likely current limiter and confidence.
2. **Data quality:** missing fields, sensor concerns, and comparability rating.
3. **Run comparison:** a compact table with duration, metric, decoupling, RPE change, carbohydrate and fluid per hour, conditions, first change and onset, and 24–48 hour recovery.
4. **What changed first:** distinguish cardiovascular cost, respiratory strain, movement or leg output, gastrointestinal tolerance, cognition, and generalized fatigue.
5. **Hypotheses:** ranked, with supporting and conflicting evidence.
6. **Next four weeks:** one primary intervention, one controlled comparison, and what to record.
7. **What would change the conclusion:** missing data or future observations that could overturn it.
8. **Safety note:** include only when symptoms warrant it.

Use the user's language and direct wording appropriate for a coach and runner. Distinguish measurement, inference, and coaching judgment explicitly.

## Safety boundary

Stop performance interpretation and recommend appropriate clinical evaluation when the record includes chest pain, fainting, neurological symptoms, severe breathing difficulty beyond expected exertion, dark urine with severe muscle pain, blood in stool or vomit, persistent inability to keep fluids down, acute injury, pain that changes gait, or symptoms that persist or worsen outside training.

## Resources

- Read `references/data-schema.md` when collecting, cleaning, or requesting data.
- Read `references/interpretation.md` when comparing runs or choosing a training emphasis.
- Run `scripts/summarize_durability.py` for compatible CSV summaries; use its output as normalization support, not as an automatic diagnosis.
- Run `scripts/fit_to_summary.py` for Garmin FIT files. It needs the optional `fitparse` dependency (see its header for one-line setup; install it in a venv to keep the core scripts stdlib-only), and chains into the CSV summarizer without intermediate files:

```bash
python3 -m venv .venv && .venv/bin/pip install fitparse   # once
.venv/bin/python scripts/fit_to_summary.py run1.fit run2.fit run3.fit \
  | python3 scripts/summarize_durability.py -
```

FIT files supply heart rate, speed/power, duration, and temperature automatically. Fueling, RPE, first-change onset, and 24–48h recovery are not stored in FIT - ask the runner for them and add them to the CSV by hand. Missing fields must be reported, never invented.
