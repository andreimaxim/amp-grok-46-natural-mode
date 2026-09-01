#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_PLUGIN_SHA256 = "6d275e590f8fbaeec45c4a314505fb96bc64c2b4fca1e6201de61afdb1c441d3"
GENERATION_RE = re.compile(r"^G(\d{4})$")

errors: list[str] = []
warnings: list[str] = []


def error(message: str) -> None:
    errors.append(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        error(message)


def load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        error(f"{path.relative_to(ROOT)}: {exc}")
        return None


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def validate_fixture(suite_name: str, config: dict, required: bool) -> dict[str, dict]:
    fixture_root = ROOT / ".fixtures" / suite_name
    suite_path = fixture_root / "benchmark/suite.json"
    if not suite_path.exists():
        message = f"fixture {suite_name} is unavailable; run scripts/fetch-fixtures.sh"
        if required:
            error(message)
        else:
            warnings.append(message)
        return {}

    suite = load_json(suite_path)
    if not isinstance(suite, dict):
        return {}
    fixture_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=fixture_root,
        text=True,
        capture_output=True,
    )
    require(fixture_revision.returncode == 0, f"{fixture_root}: not a Git checkout")
    require(
        fixture_revision.stdout.strip() == config["projects"][suite_name]["repository_commit"],
        f"{fixture_root}: fixture repository commit mismatch",
    )
    runner_path = fixture_root / ".amp/plugins/experiment-runner.ts"
    fixture_config_path = fixture_root / "benchmark/official-agent.json"
    require(runner_path.is_file(), f"{fixture_root}: experiment runner is missing")
    require(fixture_config_path.is_file(), f"{fixture_root}: official agent configuration is missing")
    if runner_path.is_file():
        require(
            sha256_file(runner_path) == config["fixture_runner_sha256"],
            f"{fixture_root}: experiment runner differs from the canonical harness",
        )
    if fixture_config_path.is_file():
        require(
            sha256_file(fixture_config_path)
            == sha256_file(ROOT / "config/official-agent.json"),
            f"{fixture_root}: official agent configuration differs from the control repository",
        )
    expected_count = config["projects"][suite_name]["scenario_count"]
    scenarios = suite.get("scenarios")
    require(suite.get("suite") == suite_name, f"{suite_path}: suite name mismatch")
    require(
        suite.get("rails_revision") == config["rails_revision"],
        f"{suite_path}: Rails revision mismatch",
    )
    require(
        suite.get("expected_scenario_count") == expected_count,
        f"{suite_path}: expected count mismatch",
    )
    if not isinstance(scenarios, list):
        error(f"{suite_path}: scenarios must be an array")
        return {}
    require(len(scenarios) == expected_count, f"{suite_path}: scenario count mismatch")

    by_id: dict[str, dict] = {}
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            error(f"{suite_path}: invalid scenario record")
            continue
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str) or scenario_id in by_id:
            error(f"{suite_path}: missing or duplicate scenario ID {scenario_id!r}")
            continue
        by_id[scenario_id] = scenario
        scenario_path = ROOT / ".fixtures" / suite_name / str(scenario.get("path"))
        if not scenario_path.is_file():
            error(f"{scenario_path}: scenario file is missing")
            continue
        require(
            sha256_file(scenario_path) == scenario.get("sha256"),
            f"{scenario_path}: scenario digest mismatch",
        )
    return by_id


def validate_record(
    record_path: Path,
    expected_mode: str,
    expected_suite: str,
    scenarios: dict[str, dict],
    rails_revision: str,
) -> str | None:
    record = load_json(record_path)
    if not isinstance(record, dict):
        return None
    label = str(record_path.relative_to(ROOT))
    required = {
        "schema_version",
        "scenario_id",
        "suite",
        "scenario_path",
        "scenario_sha256",
        "mode",
        "generation",
        "thread_id",
        "completed",
        "revision_ok",
        "rails_revision",
        "final_answer_path",
        "final_answer_sha256",
        "final_answer_bytes",
    }
    require(required <= record.keys(), f"{label}: missing required response fields")
    scenario_id = record.get("scenario_id")
    require(record.get("schema_version") == 1, f"{label}: unsupported schema version")
    require(record.get("mode") == expected_mode, f"{label}: mode mismatch")
    require(record.get("suite") == expected_suite, f"{label}: suite mismatch")
    require(record.get("completed") is True, f"{label}: completed must be true")
    require(record.get("revision_ok") is True, f"{label}: revision_ok must be true")
    require(record.get("rails_revision") == rails_revision, f"{label}: Rails revision mismatch")
    require(isinstance(record.get("thread_id"), str) and record["thread_id"].startswith("T-"), f"{label}: invalid thread ID")

    scenario = scenarios.get(scenario_id) if isinstance(scenario_id, str) else None
    require(scenario is not None, f"{label}: unknown scenario ID {scenario_id!r}")
    if scenario:
        require(record.get("scenario_path") == scenario["path"], f"{label}: scenario path mismatch")
        require(record.get("scenario_sha256") == scenario["sha256"], f"{label}: scenario digest mismatch")

    answer_rel = record.get("final_answer_path")
    if not isinstance(answer_rel, str):
        error(f"{label}: invalid final answer path")
    else:
        answer_path = ROOT / answer_rel
        if not answer_path.is_file():
            error(f"{label}: final answer file is missing")
        else:
            answer = answer_path.read_bytes()
            require(bool(answer), f"{label}: final answer is empty")
            require(sha256_bytes(answer) == record.get("final_answer_sha256"), f"{label}: final answer digest mismatch")
            require(len(answer) == record.get("final_answer_bytes"), f"{label}: final answer byte count mismatch")
    return record.get("thread_id") if isinstance(record.get("thread_id"), str) else None


def validate_references(
    config: dict,
    fixtures: dict[str, dict[str, dict]],
    required: bool,
) -> None:
    thread_ids: list[str] = []
    modes = config["fixed_references"]["modes"]
    for mode in modes:
        for suite_name in ("small", "large"):
            manifest_path = ROOT / "references" / mode / suite_name / "manifest.json"
            if not manifest_path.exists():
                if required:
                    error(f"{manifest_path.relative_to(ROOT)}: fixed reference manifest is missing")
                continue
            manifest = load_json(manifest_path)
            if not isinstance(manifest, dict):
                continue
            records = manifest.get("records")
            expected_count = config["projects"][suite_name]["scenario_count"]
            require(manifest.get("schema_version") == 1, f"{manifest_path}: unsupported schema version")
            require(manifest.get("mode") == mode, f"{manifest_path}: mode mismatch")
            require(manifest.get("suite") == suite_name, f"{manifest_path}: suite mismatch")
            require(manifest.get("rails_revision") == config["rails_revision"], f"{manifest_path}: Rails revision mismatch")
            if not isinstance(records, list):
                error(f"{manifest_path}: records must be an array")
                continue
            require(len(records) == expected_count, f"{manifest_path}: record count mismatch")
            require(len(set(records)) == len(records), f"{manifest_path}: duplicate record paths")
            seen_scenarios: set[str] = set()
            for record_rel in records:
                if not isinstance(record_rel, str):
                    error(f"{manifest_path}: invalid record path")
                    continue
                record_path = ROOT / record_rel
                if not record_path.is_file():
                    error(f"{record_rel}: response record is missing")
                    continue
                record = load_json(record_path)
                if isinstance(record, dict) and isinstance(record.get("scenario_id"), str):
                    seen_scenarios.add(record["scenario_id"])
                thread_id = validate_record(
                    record_path,
                    mode,
                    suite_name,
                    fixtures[suite_name],
                    config["rails_revision"],
                )
                if thread_id:
                    thread_ids.append(thread_id)
            require(seen_scenarios == set(fixtures[suite_name]), f"{manifest_path}: scenario coverage mismatch")
    require(len(thread_ids) == len(set(thread_ids)), "fixed references contain duplicate generation thread IDs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-to-run", action="store_true")
    args = parser.parse_args()

    for path in sorted((ROOT / "schemas").glob("*.json")):
        load_json(path)

    config = load_json(ROOT / "experiment.json")
    state = load_json(ROOT / "state.json")
    current = load_json(ROOT / "prompts/current.json")
    official = load_json(ROOT / "config/official-agent.json")
    if not all(isinstance(item, dict) for item in (config, state, current, official)):
        return 1
    assert isinstance(config, dict) and isinstance(state, dict)
    assert isinstance(current, dict) and isinstance(official, dict)

    require(config.get("schema_version") == 1, "experiment.json: unsupported schema version")
    require(config.get("stopping_rule") == "first_generation_passing_large_and_content_gates", "experiment.json: stopping rule changed")
    require(config.get("maximum_candidate_only_material_regressions") == 0, "experiment.json: content gate changed")
    require(config["projects"]["small"].get("candidate_preference_threshold") == 4, "experiment.json: small threshold changed")
    require(config["projects"]["large"].get("candidate_preference_threshold") == 48, "experiment.json: large threshold changed")
    require(
        sha256_file(ROOT / "harness/rails-experiment-runner.ts")
        == config.get("fixture_runner_sha256"),
        "experiment.json: fixture runner digest mismatch",
    )

    plugin_path = ROOT / "grok-46-mode.ts"
    require(sha256_file(plugin_path) == EXPECTED_PLUGIN_SHA256, "grok-46-mode.ts differs from the restored official baseline")
    require(official.get("official_source_sha256") == EXPECTED_PLUGIN_SHA256, "official-agent.json: source digest mismatch")
    extraction = subprocess.run(
        ["node", "scripts/extract-official-baseline.mjs", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if extraction.returncode:
        error(extraction.stderr.strip() or extraction.stdout.strip() or "official baseline extraction failed")

    generation_files = sorted((ROOT / "prompts/generations").glob("G????.json"))
    generations: dict[str, dict] = {}
    for metadata_path in generation_files:
        metadata = load_json(metadata_path)
        if not isinstance(metadata, dict):
            continue
        generation = metadata.get("generation")
        if not isinstance(generation, str) or not GENERATION_RE.match(generation):
            error(f"{metadata_path}: invalid generation ID")
            continue
        require(metadata_path.stem == generation, f"{metadata_path}: generation filename mismatch")
        prompt_path = ROOT / str(metadata.get("prompt_path"))
        require(prompt_path == ROOT / f"prompts/generations/{generation}.md", f"{metadata_path}: prompt path mismatch")
        if prompt_path.is_file():
            require(sha256_file(prompt_path) == metadata.get("prompt_sha256"), f"{metadata_path}: prompt digest mismatch")
        else:
            error(f"{prompt_path}: prompt is missing")
        if metadata.get("kind") == "candidate" and prompt_path.is_file():
            prompt = prompt_path.read_text()
            require(not re.search(r"\b[SL]\d{2}\b", prompt), f"{prompt_path}: scenario ID leaked into candidate prompt")
            require(config["rails_revision"] not in prompt, f"{prompt_path}: Rails revision leaked into candidate prompt")
            require("48/50" not in prompt and "4/5" not in prompt, f"{prompt_path}: gate score leaked into candidate prompt")
        generations[generation] = metadata

    require("G0000" in generations, "G0000 metadata is missing")
    for generation, metadata in generations.items():
        parent = metadata.get("parent_generation")
        if generation == "G0000":
            require(parent is None and metadata.get("kind") == "official_baseline", "G0000 must be the parentless official baseline")
        else:
            require(parent in generations, f"{generation}: parent generation does not exist")
            if isinstance(parent, str):
                require(parent < generation, f"{generation}: parent must precede candidate")

    current_generation = current.get("generation")
    require(current_generation in generations, "prompts/current.json: unknown generation")
    if current_generation in generations:
        require(current.get("prompt_path") == generations[current_generation].get("prompt_path"), "prompts/current.json: prompt path mismatch")
        require(current.get("prompt_sha256") == generations[current_generation].get("prompt_sha256"), "prompts/current.json: prompt digest mismatch")

    phase = state.get("phase")
    require(phase in {"bootstrap_references", "ready", "evaluating", "stopped"}, "state.json: invalid phase")
    champion = state.get("champion_generation")
    active = state.get("active_generation")
    final = state.get("final_generation")
    require(champion in generations, "state.json: unknown champion")
    if active is None:
        require(current_generation == champion, "state.json: current prompt must be champion when no generation is active")
    else:
        require(active in generations, "state.json: unknown active generation")
        require(current_generation == active, "state.json: current prompt must be active generation")
        require(phase == "evaluating", "state.json: active generation requires evaluating phase")
    if state.get("stopped"):
        require(phase == "stopped" and final in generations, "state.json: stopped experiment requires a final generation")
        require(final == champion, "state.json: final generation must be champion")
    else:
        require(final is None, "state.json: non-stopped experiment cannot have a final generation")
    next_generation = state.get("next_generation")
    expected_next = f"G{max(int(GENERATION_RE.match(item).group(1)) for item in generations) + 1:04d}"
    require(next_generation == expected_next, f"state.json: next_generation must be {expected_next}")

    plugin_source = (ROOT / ".amp/plugins/candidate-mode.ts").read_text()
    require("grok46-baseline" in plugin_source and "grok46-candidate" in plugin_source, "candidate plugin does not register both experiment modes")

    fixtures_required = args.ready_to_run or phase != "bootstrap_references"
    fixtures = {
        suite: validate_fixture(suite, config, fixtures_required)
        for suite in ("small", "large")
    }
    validate_references(config, fixtures, args.ready_to_run)
    if args.ready_to_run:
        require(phase != "bootstrap_references", "state.json: reference bootstrap is not complete")

    for path in sorted((ROOT / "runs").glob("G????/summary.json")):
        load_json(path)
    for path in sorted((ROOT / "failures").glob("G????.json")):
        load_json(path)

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if errors:
        for message in errors:
            print(f"error: {message}", file=sys.stderr)
        return 1
    print(f"experiment repository valid: {len(generations)} generation(s)")
    if args.ready_to_run:
        print("fixed references valid: 110 responses across 55 scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
