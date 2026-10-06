#!/usr/bin/env python3
"""Normalize long-run summaries and calculate simplified durability metrics."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from pathlib import Path


def number(row: dict[str, str], key: str, required: bool = False) -> float | None:
    raw = (row.get(key) or "").strip()
    if not raw:
        if required:
            raise ValueError(f"missing required field {key}")
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be numeric, got {raw!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"{key} must be finite")
    return value


def fmt(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def choose_output(row: dict[str, str], metric: str) -> tuple[str, float, float]:
    first_power = number(row, "first_power_w")
    second_power = number(row, "second_power_w")
    first_speed = number(row, "first_speed_kmh")
    second_speed = number(row, "second_speed_kmh")

    if metric in {"auto", "speed"} and first_speed is not None and second_speed is not None:
        return "speed", first_speed, second_speed
    if metric in {"auto", "power"} and first_power is not None and second_power is not None:
        return "power", first_power, second_power
    raise ValueError("provide a matched first/second power or speed pair")


def analyze_row(row: dict[str, str], metric: str) -> dict[str, object]:
    duration = number(row, "duration_min", required=True)
    first_hr = number(row, "first_hr", required=True)
    second_hr = number(row, "second_hr", required=True)
    assert duration is not None and first_hr is not None and second_hr is not None
    if duration <= 0 or first_hr <= 0 or second_hr <= 0:
        raise ValueError("duration and heart rates must be positive")

    output_kind, first_output, second_output = choose_output(row, metric)
    if first_output <= 0 or second_output <= 0:
        raise ValueError("speed or power values must be positive")

    ef_first = first_output / first_hr
    ef_second = second_output / second_hr
    carbs = number(row, "carbs_g")
    fluid = number(row, "fluid_ml")
    rpe_first = number(row, "rpe_first")
    rpe_second = number(row, "rpe_second")

    return {
        **row,
        "duration": duration,
        "metric": output_kind,
        "decoupling": (ef_first - ef_second) / ef_first * 100,
        "output_drop": (first_output - second_output) / first_output * 100,
        "carbs_h": None if carbs is None else carbs / duration * 60,
        "fluid_h": None if fluid is None else fluid / duration * 60,
        "rpe_delta": None if rpe_first is None or rpe_second is None else rpe_second - rpe_first,
        "first_change": number(row, "first_change_min"),
        "temp": number(row, "temp_c"),
        "humidity": number(row, "humidity_pct"),
        "elevation": number(row, "elevation_gain_m"),
    }


def numeric_values(rows: list[dict[str, object]], key: str) -> list[float]:
    return [float(row[key]) for row in rows if row[key] is not None]


def value_spread(values: list[float]) -> float | None:
    return None if len(values) < 2 else max(values) - min(values)


def quality_flags(rows: list[dict[str, object]]) -> list[str]:
    flags: list[str] = []
    if len({str(row["metric"]) for row in rows}) > 1:
        flags.append("记录混用了速度与功率效率因子，不应直接比较它们的解耦率。")

    durations = numeric_values(rows, "duration")
    if max(durations) / min(durations) > 1.15:
        flags.append("各次训练时长相差超过15%。")

    temp_spread = value_spread(numeric_values(rows, "temp"))
    if temp_spread is not None and temp_spread > 5:
        flags.append("各次训练气温相差超过5°C。")

    humidity_spread = value_spread(numeric_values(rows, "humidity"))
    if humidity_spread is not None and humidity_spread > 15:
        flags.append("各次训练湿度相差超过15个百分点。")

    elevations = numeric_values(rows, "elevation")
    if len(elevations) >= 2 and min(elevations) > 0 and max(elevations) / min(elevations) > 1.2:
        flags.append("各次训练累计爬升相差超过20%。")

    for field in ("carbs_h", "fluid_h", "rpe_delta", "first_change"):
        if sum(row[field] is not None for row in rows) < len(rows):
            flags.append(f"部分训练缺少 {field.replace('_', ' ')}。")
    return flags


def render(rows: list[dict[str, object]]) -> str:
    lines = [
        "# 跑步耐久性数据摘要",
        "",
        "| 日期 | 时长（分钟） | 指标 | 解耦率 | 输出下降 | RPE变化 | 碳水（克/时） | 液体（毫升/时） | 首次变化（分钟） | 首次变化类型 |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {date} | {duration} | {metric} | {dec} | {drop} | {rpe} | {carbs} | {fluid} | {change} | {kind} |".format(
                date=row.get("date") or "—",
                duration=fmt(float(row["duration"]), 0),
                metric=row["metric"],
                dec=fmt(float(row["decoupling"])),
                drop=fmt(float(row["output_drop"])),
                rpe=fmt(row["rpe_delta"] if isinstance(row["rpe_delta"], float) else None),
                carbs=fmt(row["carbs_h"] if isinstance(row["carbs_h"], float) else None),
                fluid=fmt(row["fluid_h"] if isinstance(row["fluid_h"], float) else None, 0),
                change=fmt(row["first_change"] if isinstance(row["first_change"], float) else None, 0),
                kind=row.get("first_change_type") or "—",
            )
        )

    decoupling = numeric_values(rows, "decoupling")
    lines.extend(["", "## 描述性汇总", ""])
    lines.append(f"- 解耦率中位数：{statistics.median(decoupling):.1f}%（范围 {min(decoupling):.1f}%–{max(decoupling):.1f}%）。")
    onset = numeric_values(rows, "first_change")
    if onset:
        lines.append(f"- 记录到的首次变化时间中位数：{statistics.median(onset):.0f}分钟。")

    flags = quality_flags(rows)
    lines.extend(["", "## 可比性提示", ""])
    if flags:
        lines.extend(f"- {flag}" for flag in flags)
    else:
        lines.append("- 未发现明显的数值可比性问题；仍需检查路线、路面、停顿、强度、睡眠、疾病与传感器质量。")

    lines.extend([
        "",
        "> 本结果只负责统一计算口径。选择训练干预前，还需结合变化出现时间、症状、环境、恢复和其他解释；5%不是通用合格线。",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path,
                        help="CSV containing summarized long-run data; "
                             "use '-' to read stdin (e.g. piped from fit_to_summary.py)")
    parser.add_argument("--metric", choices=("auto", "speed", "power"), default="auto")
    args = parser.parse_args()

    try:
        # '-' reads stdin so the two scripts can be chained without a temp file
        handle = sys.stdin if str(args.csv_file) == "-" else args.csv_file.open(encoding="utf-8-sig", newline="")
        with handle:
            source_rows = list(csv.DictReader(handle))
        if not source_rows:
            raise ValueError("CSV has no data rows")
        analyzed = []
        for index, row in enumerate(source_rows, start=2):
            try:
                analyzed.append(analyze_row(row, args.metric))
            except ValueError as exc:
                raise ValueError(f"row {index}: {exc}") from exc
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(render(analyzed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
