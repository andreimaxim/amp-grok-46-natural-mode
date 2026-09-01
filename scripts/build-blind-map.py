#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic, balanced candidate/baseline A/B map."
    )
    parser.add_argument("--suite", choices=("small", "large"), required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    suite_path = ROOT / ".fixtures" / args.suite / "benchmark/suite.json"
    suite = json.loads(suite_path.read_text())
    scenario_ids = [scenario["id"] for scenario in suite["scenarios"]]
    ordered = sorted(
        scenario_ids,
        key=lambda scenario_id: hashlib.sha256(
            f"{args.seed}\0{scenario_id}".encode()
        ).digest(),
    )
    candidate_a = set(ordered[: (len(ordered) + 1) // 2])
    assignments = [
        {
            "scenario_id": scenario_id,
            "candidate_label": "A" if scenario_id in candidate_a else "B",
            "baseline_label": "B" if scenario_id in candidate_a else "A",
        }
        for scenario_id in scenario_ids
    ]
    result = {
        "$schema": "../../../../schemas/blind-map.schema.json",
        "schema_version": 1,
        "suite": args.suite,
        "seed": args.seed,
        "assignments": assignments,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{json.dumps(result, indent=2)}\n")
    print(
        f"wrote balanced map for {len(assignments)} cases "
        f"({len(candidate_a)} candidate=A, {len(assignments) - len(candidate_a)} candidate=B)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
