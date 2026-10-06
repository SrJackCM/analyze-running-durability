#!/usr/bin/env python3
"""Summarize Garmin FIT files into durability CSV rows (see references/data-schema.md).

Usage:
    fit_to_summary.py run1.fit run2.fit ... [--min-minutes N] [--metric auto|speed|power]

CSV goes to stdout; notes and warnings go to stderr, so this pipes directly
into the CSV summarizer without writing intermediate files:

    fit_to_summary.py run*.fit | summarize_durability.py -

Requires the optional fitparse package. One-time setup (keeps the core
scripts stdlib-only):

    python3 -m venv .venv && .venv/bin/pip install fitparse
    .venv/bin/python scripts/fit_to_summary.py run*.fit \
        | python3 scripts/summarize_durability.py -
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

# Columns emitted; names follow references/data-schema.md.
FIELDS = ["date", "duration_min", "first_hr", "second_hr",
          "first_speed_kmh", "second_speed_kmh",
          "first_power_w", "second_power_w", "temp_c"]


def read_records(path: Path):
    """Yield (timestamp, heart_rate, power, temperature, distance_m) per record.

    Missing fields stay None; the half statistics below filter them out.
    """
    # fitparse is an optional dependency: give a setup hint instead of a bare ImportError
    try:
        from fitparse import FitFile
    except ImportError as exc:
        raise SystemExit(
            "fitparse is required for FIT input. Set it up once with:\n"
            "  python3 -m venv .venv && .venv/bin/pip install fitparse\n"
            "then re-run with .venv/bin/python."
        ) from exc

    for rec in FitFile(str(path)).get_messages("record"):
        def value(name: str):
            # fitparse returns FieldData; .value is the raw numeric value
            field = rec.get(name)
            return None if field is None else field.value

        timestamp = value("timestamp")
        if timestamp is None:
            continue  # untimestamped rows cannot be placed on the timeline
        yield (timestamp, value("heart_rate"), value("power"),
               value("temperature"), value("distance"))


def derive_date(path: Path, first_timestamp) -> str:
    """Prefer the timestamp stored in the FIT file; fall back to an 8-digit
    date prefix in the filename (a common export naming convention)."""
    if isinstance(first_timestamp, datetime):
        return first_timestamp.strftime("%Y%m%d")
    m = re.match(r"^(\d{8})", path.name)
    return m.group(1) if m else ""


def half_stats(seg):
    """Return (avg heart rate, avg speed km/h, avg power W, avg temp C) for a half.

    Heart rate: mean after dropping 0 and 255 (Garmin's invalid placeholder).
    Speed: distance delta over time delta across the segment - robust against
    pauses and sampling gaps; None when no usable distance is present.
    Power: mean of positive values; None when the device recorded none.
    Temperature: mean after dropping sensor outliers above 60 C.
    """
    hrs = [r[1] for r in seg if r[1] is not None and 0 < r[1] < 255]
    avg_hr = sum(hrs) / len(hrs) if hrs else None

    avg_spd = None
    if len(seg) >= 2:
        dt = (seg[-1][0] - seg[0][0]).total_seconds()
        dd = (seg[-1][4] or 0) - (seg[0][4] or 0)  # cumulative meters, delta per half
        if dt > 0 and dd > 0:
            avg_spd = dd / dt * 3.6

    pows = [r[2] for r in seg if r[2] is not None and r[2] > 0]
    avg_pwr = sum(pows) / len(pows) if pows else None

    temps = [r[3] for r in seg if r[3] is not None and r[3] < 60]
    avg_temp = sum(temps) / len(temps) if temps else None

    return avg_hr, avg_spd, avg_pwr, avg_temp


def summarize(path: Path, min_minutes: float):
    """One FIT file -> schema row dict, or None when shorter than min_minutes.

    The file is parsed exactly once; speed is preferred over power so mixed
    trends never combine an efficiency factor from both (see SKILL.md).
    """
    records = list(read_records(path))
    if len(records) < 30:
        raise ValueError(f"only {len(records)} record messages")

    total_s = (records[-1][0] - records[0][0]).total_seconds()
    if total_s / 60 < min_minutes:
        return None

    # Split at the elapsed-time midpoint (documented limitation: for long
    # trail sessions with big hiking/stopping blocks, a distance midpoint
    # can be more representative).
    mid = total_s / 2
    first = [r for r in records if (r[0] - records[0][0]).total_seconds() < mid]
    second = [r for r in records if (r[0] - records[0][0]).total_seconds() >= mid]
    hr1, spd1, pwr1, _ = half_stats(first)
    hr2, spd2, pwr2, temp2 = half_stats(second)

    def r1(v):
        return None if v is None else round(v, 1)

    row = {
        "date": derive_date(path, records[0][0]),
        "duration_min": round(total_s / 60, 1),
        "first_hr": r1(hr1),
        "second_hr": r1(hr2),
        # Mid-run temperature: second-half mean (the conditions the body actually ran in)
        "temp_c": r1(temp2),
    }
    if spd1 is not None and spd2 is not None:
        row["first_speed_kmh"] = round(spd1, 2)
        row["second_speed_kmh"] = round(spd2, 2)
    elif pwr1 is not None and pwr2 is not None:
        row["first_power_w"] = r1(pwr1)
        row["second_power_w"] = r1(pwr2)
    else:
        raise ValueError("no usable speed or power data in both halves")
    return row


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize Garmin FIT files into durability CSV (stdout)")
    parser.add_argument("files", nargs="+", type=Path,
                        help="one or more Garmin FIT files")
    parser.add_argument("--min-minutes", type=float, default=45.0,
                        help="skip sessions shorter than this (default: 45)")
    parser.add_argument("--metric", choices=("auto", "speed", "power"),
                        default="auto",
                        help="auto: speed if present, else power (default: auto)")
    args = parser.parse_args()

    rows = []
    for path in args.files:
        if not path.exists():
            print(f"error: not found: {path}", file=sys.stderr)
            return 2
        try:
            row = summarize(path, args.min_minutes)
        except ValueError as exc:
            print(f"warning: skipped {path.name}: {exc}", file=sys.stderr)
            continue
        if row is None:
            print(f"note: skipped {path.name}: shorter than {args.min_minutes:g} min",
                  file=sys.stderr)
            continue
        # --metric filters what gets emitted (auto keeps whichever pair exists)
        if args.metric == "speed" and "first_speed_kmh" not in row:
            print(f"warning: skipped {path.name}: no speed data (--metric speed)",
                  file=sys.stderr)
            continue
        if args.metric == "power" and "first_power_w" not in row:
            print(f"warning: skipped {path.name}: no power data (--metric power)",
                  file=sys.stderr)
            continue
        rows.append(row)

    if not rows:
        print("error: no usable sessions", file=sys.stderr)
        return 1

    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
