#!/usr/bin/env python3
"""Check that the control repository is internally consistent.

Without flags this validates configuration, generations, state, and whatever
reference and run artifacts exist. With --ready-to-run it additionally requires
both fixtures and the complete reference corpus, which every generation needs.
"""

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
SUITES = ("small", "large")

errors: list[str] = []
warnings: list[str] = []


def error(message: str) -> None:
    errors.append(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        error(message)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        error(f"{rel(path)}: {exc}")
        return None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generation_number(generation: str) -> int:
    return int(GENERATION_RE.match(generation).group(1))


def check_prompt_leaks(generation: str, parent: str | None, config: dict) -> None:
    """Flag scenario IDs, the Rails revision, or gate scores that a prompt introduces over its parent."""
    prompt_path = ROOT / f"prompts/generations/{generation}.md"
    if not prompt_path.is_file():
        return
    prompt = prompt_path.read_text()
    parent_prompt = (ROOT / f"prompts/generations/{parent}.md").read_text() if parent else ""
    id_pattern = re.compile(r"\b[SL]\d{2}\b")
    introduced = set(id_pattern.findall(prompt)) - set(id_pattern.findall(parent_prompt))
    require(not introduced, f"{rel(prompt_path)}: scenario-like IDs {sorted(introduced)} introduced into the prompt")
    require(config["rails_revision"] not in prompt, f"{rel(prompt_path)}: Rails revision leaked into the prompt")
    for score in ("48/50", "4/5", "48 of 50", "4 of 5"):
        require(score not in prompt or score in parent_prompt, f"{rel(prompt_path)}: gate score {score!r} leaked into the prompt")


def validate_fixture(suite_name: str, config: dict, required: bool) -> set[str]:
    """Return the scenario IDs of a fixture, or an empty set when unavailable."""
    fixture_root = ROOT / ".fixtures" / suite_name
    suite_path = fixture_root / "benchmark/suite.json"
    if not suite_path.exists():
        message = f"fixture {suite_name} is unavailable; run scripts/fetch-fixtures.sh"
        (error if required else warnings.append)(message)
        return set()

    suite_config = config["suites"][suite_name]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=fixture_root, text=True, capture_output=True)
    require(head.returncode == 0, f"{rel(fixture_root)}: not a Git checkout")
    require(head.stdout.strip() == suite_config["repository_commit"], f"{rel(fixture_root)}: fixture commit differs from experiment.json")

    runner_path = fixture_root / ".amp/plugins/experiment-runner.ts"
    if runner_path.is_file():
        require(sha256_file(runner_path) == config["fixture_runner_sha256"], f"{rel(runner_path)}: differs from harness/rails-experiment-runner.ts")
    else:
        error(f"{rel(runner_path)}: experiment runner is missing")
    fixture_config_path = fixture_root / "benchmark/official-agent.json"
    if fixture_config_path.is_file():
        require(
            sha256_file(fixture_config_path) == sha256_file(ROOT / "config/official-agent.json"),
            f"{rel(fixture_config_path)}: differs from config/official-agent.json",
        )
    else:
        error(f"{rel(fixture_config_path)}: official agent configuration is missing")

    suite = load_json(suite_path)
    if not isinstance(suite, dict) or not isinstance(suite.get("scenarios"), list):
        error(f"{rel(suite_path)}: invalid suite manifest")
        return set()
    require(suite.get("suite") == suite_name, f"{rel(suite_path)}: suite name mismatch")
    require(suite.get("rails_revision") == config["rails_revision"], f"{rel(suite_path)}: Rails revision mismatch")
    scenario_ids = [scenario.get("id") for scenario in suite["scenarios"] if isinstance(scenario, dict)]
    require(len(scenario_ids) == suite_config["scenario_count"], f"{rel(suite_path)}: scenario count mismatch")
    require(len(set(scenario_ids)) == len(scenario_ids), f"{rel(suite_path)}: duplicate scenario IDs")
    for scenario in suite["scenarios"]:
        if isinstance(scenario, dict) and not (fixture_root / str(scenario.get("path"))).is_file():
            error(f"{rel(suite_path)}: scenario file {scenario.get('path')} is missing")
    return {scenario_id for scenario_id in scenario_ids if isinstance(scenario_id, str)}


def validate_record(record_path: Path, suite_name: str, mode: str | None, generation: str | None) -> str | None:
    """Validate one answer record and return its thread ID."""
    record = load_json(record_path)
    if not isinstance(record, dict):
        return None
    label = rel(record_path)
    scenario_id = record_path.name.removesuffix(".json")
    require(record.get("schema_version") == 2, f"{label}: unsupported schema version")
    require(record.get("scenario_id") == scenario_id, f"{label}: scenario ID does not match filename")
    require(record.get("suite") == suite_name, f"{label}: suite mismatch")
    require(record.get("mode") == mode, f"{label}: mode mismatch")
    require(record.get("generation") == generation, f"{label}: generation mismatch")
    thread_id = record.get("thread_id")
    require(isinstance(thread_id, str) and thread_id.startswith("T-"), f"{label}: invalid thread ID")
    for key, expected in (("answer_path", f"{scenario_id}.md"), ("transcript_path", f"{scenario_id}.thread.md")):
        value = record.get(key)
        expected_path = record_path.with_name(expected)
        require(value == rel(expected_path), f"{label}: {key} must be {rel(expected_path)}")
        if not expected_path.is_file():
            error(f"{rel(expected_path)}: missing")
        elif expected_path.stat().st_size == 0:
            error(f"{rel(expected_path)}: empty")
    return thread_id if isinstance(thread_id, str) else None


def validate_answer_set(
    directory: Path,
    suite_name: str,
    scenario_ids: set[str],
    mode: str | None,
    generation: str | None,
    required: bool,
) -> tuple[set[str], list[str]]:
    """Validate every record under directory; return covered scenario IDs and thread IDs."""
    if not directory.is_dir():
        if required:
            error(f"{rel(directory)}: missing")
        return set(), []
    records = sorted(path for path in directory.glob("[SL]??.json"))
    thread_ids = [validate_record(path, suite_name, mode, generation) for path in records]
    covered = {path.name.removesuffix(".json") for path in records}
    if scenario_ids:
        require(covered <= scenario_ids, f"{rel(directory)}: records for unknown scenarios {sorted(covered - scenario_ids)}")
        if required:
            require(covered == scenario_ids, f"{rel(directory)}: missing scenarios {sorted(scenario_ids - covered)}")
    return covered, [thread_id for thread_id in thread_ids if thread_id]


def validate_references(config: dict, fixtures: dict[str, set[str]], required: bool) -> list[str]:
    thread_ids: list[str] = []
    for mode in config["reference_modes"]:
        for suite_name in SUITES:
            _, ids = validate_answer_set(
                ROOT / "references" / mode / suite_name, suite_name, fixtures[suite_name], mode, None, required
            )
            thread_ids.extend(ids)
    return thread_ids


def validate_judgments(directory: Path, covered: set[str]) -> int:
    matches = 0
    for scenario_id in sorted(covered):
        judgment_path = directory / f"{scenario_id}.judgment.json"
        if not judgment_path.is_file():
            error(f"{rel(judgment_path)}: missing")
            continue
        judgment = load_json(judgment_path)
        if not isinstance(judgment, dict):
            continue
        require(judgment.get("scenario_id") == scenario_id, f"{rel(judgment_path)}: scenario ID mismatch")
        require(isinstance(judgment.get("match"), bool), f"{rel(judgment_path)}: match must be a boolean")
        require(bool(judgment.get("rationale")), f"{rel(judgment_path)}: rationale is required")
        matches += judgment.get("match") is True
    return matches


def validate_run(generation: str, metadata: dict, config: dict, fixtures: dict[str, set[str]]) -> dict | None:
    run_root = ROOT / "runs" / generation
    summary_path = run_root / "summary.json"
    if not run_root.is_dir():
        return None
    summary = load_json(summary_path) if summary_path.exists() else None
    if summary_path.exists() and not isinstance(summary, dict):
        return None

    results: dict[str, dict | None] = {}
    for suite_name in SUITES:
        directory = run_root / suite_name
        if not directory.is_dir():
            results[suite_name] = None
            continue
        covered, _ = validate_answer_set(directory, suite_name, fixtures[suite_name], None, generation, required=False)
        matches = validate_judgments(directory, covered)
        results[suite_name] = {"scenario_count": len(covered), "matches": matches}

    if summary is None:
        return None
    label = rel(summary_path)
    require(summary.get("schema_version") == 2, f"{label}: unsupported schema version")
    require(summary.get("generation") == generation, f"{label}: generation mismatch")
    require(summary.get("parent_generation") == metadata.get("parent_generation"), f"{label}: parent mismatch")
    for suite_name in SUITES:
        suite_config = config["suites"][suite_name]
        reported = summary.get(suite_name)
        observed = results[suite_name]
        if reported is None:
            require(observed is None, f"{label}: {suite_name} answers exist but the summary omits them")
            continue
        if not isinstance(reported, dict) or observed is None:
            error(f"{label}: {suite_name} summary without answers")
            continue
        require(reported.get("scenario_count") == suite_config["scenario_count"] == observed["scenario_count"], f"{label}: {suite_name} scenario count mismatch")
        require(reported.get("matches") == observed["matches"], f"{label}: {suite_name} matches ({reported.get('matches')}) differ from judgments ({observed['matches']})")
        require(reported.get("threshold") == suite_config["match_threshold"], f"{label}: {suite_name} threshold mismatch")
        require(reported.get("passed") == (observed["matches"] >= suite_config["match_threshold"]), f"{label}: {suite_name} passed flag mismatch")

    small, large = summary.get("small"), summary.get("large")
    small_passed = isinstance(small, dict) and small.get("passed") is True
    require(isinstance(small, dict), f"{label}: small suite result is required")
    if large is not None:
        require(small_passed, f"{label}: large suite ran without a small pass")
    decision = summary.get("decision")
    if decision == "failed_small":
        require(not small_passed and large is None, f"{label}: failed_small contradicts results")
    elif decision == "failed_large":
        require(small_passed and isinstance(large, dict) and large.get("passed") is False, f"{label}: failed_large contradicts results")
    elif decision == "final":
        require(small_passed and isinstance(large, dict) and large.get("passed") is True, f"{label}: final contradicts results")
    else:
        error(f"{label}: invalid decision {decision!r}")
    failure_note = ROOT / "failures" / f"{generation}.md"
    if decision in {"failed_small", "failed_large"}:
        require(failure_note.is_file() and failure_note.stat().st_size > 0, f"{rel(failure_note)}: failure note is required after {decision}")
    return summary


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

    require(config.get("schema_version") == 2, "experiment.json: unsupported schema version")
    require(config.get("reference_modes") == ["grok46-high", "grok46-ultra"], "experiment.json: reference modes changed")
    require(config.get("judge_mode") == "high", "experiment.json: judge mode changed")
    require(config["suites"]["small"].get("match_threshold") == 4, "experiment.json: small threshold changed")
    require(config["suites"]["large"].get("match_threshold") == 48, "experiment.json: large threshold changed")
    require(config.get("large_requires_small_pass") is True, "experiment.json: large must require a small pass")
    require(
        sha256_file(ROOT / "harness/rails-experiment-runner.ts") == config.get("fixture_runner_sha256"),
        "experiment.json: fixture runner digest mismatch",
    )

    require(sha256_file(ROOT / "grok-46-mode.ts") == EXPECTED_PLUGIN_SHA256, "grok-46-mode.ts differs from the restored official baseline")
    require(official.get("official_source_sha256") == EXPECTED_PLUGIN_SHA256, "official-agent.json: source digest mismatch")
    extraction = subprocess.run(["node", "scripts/extract-official-baseline.mjs", "--check"], cwd=ROOT, text=True, capture_output=True)
    if extraction.returncode:
        error(extraction.stderr.strip() or extraction.stdout.strip() or "official baseline extraction failed")

    generations: dict[str, dict] = {}
    for metadata_path in sorted((ROOT / "prompts/generations").glob("G????.json")):
        metadata = load_json(metadata_path)
        if not isinstance(metadata, dict):
            continue
        generation = metadata.get("generation")
        if not isinstance(generation, str) or not GENERATION_RE.match(generation):
            error(f"{rel(metadata_path)}: invalid generation ID")
            continue
        require(metadata_path.stem == generation, f"{rel(metadata_path)}: filename does not match generation")
        prompt_path = ROOT / str(metadata.get("prompt_path"))
        require(prompt_path == ROOT / f"prompts/generations/{generation}.md", f"{rel(metadata_path)}: prompt path mismatch")
        if prompt_path.is_file():
            require(sha256_file(prompt_path) == metadata.get("prompt_sha256"), f"{rel(metadata_path)}: prompt was edited after its digest was recorded")
        else:
            error(f"{rel(prompt_path)}: prompt is missing")
        generations[generation] = metadata

    require("G0000" in generations, "G0000 metadata is missing")
    ordered = sorted(generations, key=generation_number)
    require([generation_number(item) for item in ordered] == list(range(len(ordered))), "generation IDs must be consecutive from G0000")
    for previous, generation in zip([None, *ordered], ordered):
        metadata = generations[generation]
        if generation == "G0000":
            require(metadata.get("parent_generation") is None and metadata.get("kind") == "official_baseline", "G0000 must be the parentless official baseline")
        else:
            require(metadata.get("parent_generation") == previous, f"{generation}: parent must be {previous}; the lineage is linear")
            require(metadata.get("kind") == "candidate", f"{generation}: kind must be candidate")
            check_prompt_leaks(generation, previous, config)

    latest = ordered[-1] if ordered else None
    require(current.get("generation") == latest, f"prompts/current.json: must point at the latest generation {latest}")
    if latest:
        require(current.get("prompt_path") == generations[latest].get("prompt_path"), "prompts/current.json: prompt path mismatch")
        require(current.get("prompt_sha256") == generations[latest].get("prompt_sha256"), "prompts/current.json: prompt digest mismatch")

    phase = state.get("phase")
    require(state.get("schema_version") == 2, "state.json: unsupported schema version")
    require(phase in {"bootstrap_references", "ready", "evaluating", "stopped"}, "state.json: invalid phase")
    require(state.get("latest_generation") == latest, f"state.json: latest_generation must be {latest}")
    active, final = state.get("active_generation"), state.get("final_generation")
    if active is not None:
        require(active == latest, "state.json: only the latest generation can be active")
        require(phase == "evaluating", "state.json: an active generation requires the evaluating phase")
    else:
        require(phase != "evaluating", "state.json: evaluating phase requires an active generation")
    if latest:
        require(state.get("next_generation") == f"G{generation_number(latest) + 1:04d}", "state.json: next_generation must follow the latest generation")

    fixtures_required = args.ready_to_run or phase != "bootstrap_references"
    fixtures = {suite: validate_fixture(suite, config, fixtures_required) for suite in SUITES}
    reference_threads = validate_references(config, fixtures, required=args.ready_to_run or phase != "bootstrap_references")
    require(len(reference_threads) == len(set(reference_threads)), "references reuse a thread ID")
    if args.ready_to_run:
        require(phase != "bootstrap_references", "state.json: reference bootstrap is not complete")

    summaries = {generation: validate_run(generation, generations[generation], config, fixtures) for generation in ordered}
    for previous, generation in zip(ordered, ordered[1:]):
        require(summaries.get(previous) is not None, f"{generation} exists but {previous} has no runs/{previous}/summary.json")
    final_summaries = [generation for generation, summary in summaries.items() if summary and summary.get("decision") == "final"]
    if state.get("stopped"):
        require(phase == "stopped" and final == latest and final in final_summaries, "state.json: stopped requires the latest generation to have a final summary")
    else:
        require(final is None and not final_summaries, "state.json: a final summary exists but the experiment is not stopped")

    plugin_source = (ROOT / ".amp/plugins/candidate-mode.ts").read_text()
    require("grok46-candidate" in plugin_source, "candidate plugin does not register grok46-candidate")

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if errors:
        for message in errors:
            print(f"error: {message}", file=sys.stderr)
        return 1
    evaluated = sum(summary is not None for summary in summaries.values())
    print(f"experiment repository valid: {len(generations)} generation(s), {evaluated} evaluated")
    if args.ready_to_run:
        print(f"references valid: {len(reference_threads)} answers across 55 scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
