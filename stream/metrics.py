# -*- coding: utf-8 -*-
"""프레임별 latency를 모아 CSV로 저장하고 요약 통계를 출력한다."""

import csv
import math
import threading
import time
from pathlib import Path


FIELDNAMES = [
    "timestamp",
    "elapsed_s",
    "frame_id",
    "warmup",
    "capture_ms",
    "resize_ms",
    "model_total_ms",
    "preprocess_ms",
    "inference_ms",
    "postprocess_ms",
    "draw_ms",
    "count_ms",
    "rules_ms",
    "encode_ms",
    "total_ms",
]

LATENCY_FIELDS = FIELDNAMES[4:]


def percentile(values, percent):
    """외부 통계 패키지 없이 선형 보간 percentile을 계산한다."""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100.0
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


class LatencyRecorder:
    """계측이 켜졌을 때만 row를 메모리에 보관하고 종료 시 한 번에 기록한다."""

    def __init__(self, output_path=None, warmup_secs=30.0):
        self.output_path = Path(output_path) if output_path else None
        self.warmup_secs = max(0.0, float(warmup_secs))
        self.started_at = time.monotonic()
        self.rows = []
        self._closed = False
        self._lock = threading.Lock()

    @property
    def enabled(self):
        return self.output_path is not None

    def add(self, frame_id, timing):
        if not self.enabled:
            return

        elapsed_s = time.monotonic() - self.started_at
        row = {
            "timestamp": "{:.6f}".format(time.time()),
            "elapsed_s": "{:.6f}".format(elapsed_s),
            "frame_id": int(frame_id),
            "warmup": int(elapsed_s < self.warmup_secs),
        }
        for field in LATENCY_FIELDS:
            row[field] = "{:.6f}".format(float(timing.get(field, 0.0)))

        with self._lock:
            if not self._closed:
                self.rows.append(row)

    def summary(self):
        with self._lock:
            measured = [row for row in self.rows if row["warmup"] == 0]

        result = {}
        for field in LATENCY_FIELDS:
            values = [float(row[field]) for row in measured]
            if not values:
                continue
            result[field] = {
                "mean": sum(values) / len(values),
                "p50": percentile(values, 50),
                "p95": percentile(values, 95),
            }
        return result

    def close(self):
        if not self.enabled:
            return

        with self._lock:
            if self._closed:
                return
            self._closed = True
            rows = list(self.rows)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        measured_count = sum(1 for row in rows if row["warmup"] == 0)
        print(
            "[metrics] CSV 저장: {} (전체 {}프레임, 측정 {}프레임)".format(
                self.output_path, len(rows), measured_count
            )
        )

        summary = self.summary()
        if not summary:
            print("[metrics] 워밍업 이후 측정값이 없습니다.")
            return

        print("\n[metrics] 단계별 latency (warm-up 제외)")
        print("{:<18s} {:>10s} {:>10s} {:>10s}".format("stage", "mean", "p50", "p95"))
        for field in LATENCY_FIELDS:
            stats = summary.get(field)
            if stats is None:
                continue
            print(
                "{:<18s} {:>9.2f}ms {:>9.2f}ms {:>9.2f}ms".format(
                    field, stats["mean"], stats["p50"], stats["p95"]
                )
            )
