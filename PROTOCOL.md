# Evolution protocol

## Goal and fixed inputs

Evolve one Grok 4.6 system-prompt lineage until one generation is preferred to the immutable official baseline on at least 48 of the 50 large-suite scenarios and has no material candidate-only correctness regressions.

The experiment is adaptive. Failures from both suites are training evidence for later generations; the 50-case suite is not a holdout. The following inputs remain fixed for the whole experiment:

- Rails revision `d59d106f94dcb7f8e748545c0ccf8a276d20f590`.
- Five small and fifty large natural-task scenario files and their suite manifests.
- One `high` response and one official-baseline response per scenario.
- Agent model, tools, reasoning effort, and compaction threshold from `config/official-agent.json`.
- Judge prompts and gate definitions in this repository.

The fixed `high` response is a communication/style target, not factual ground truth. Rails source and executed checks are the correctness authority.

## One-time reference bootstrap

Before Generation 1, run `prompts/bootstrap-references.md` in a fresh control-repository orb.

The control orb's setup creates verified sparse fixture checkouts under `.fixtures/`. The full Rails fixture projects contain the byte-identical `harness/rails-experiment-runner.ts` plugin. It creates a fresh child orb inside the fixture project, reads the scenario from the validated manifest, and sends those exact bytes with the child thread's `append` API. For fixed `high` references, the runner registers `grok46-reference-high`, an agent that extends Amp's built-in `high` mode with no identity, instructions, or tool override, preserving that mode's system prompt, preferred model, effort, and standard tools. Revision checks and experiment controls stay in setup, validation, and run metadata; never prepend or append them to scenario text.

Project-local custom modes do not travel to another Amp project. Therefore, for each suite, first create one `low` coordinator thread in the target Rails project. Coordination and verbatim collection are mechanical and do not require judge-level reasoning. Confirm `benchmark/bin/validate` passes and the `run_grok46_experiment_case` tool is available. Upload the immutable prompt to the coordinator's existing `.amp/experiment-inputs/` directory, then have it call the runner once per scenario. The runner records each child ID before sending the scenario and persists the terminal final after the child settles. Never approximate the candidate system prompt with extra user text.

After uploading the prompt, reload the coordinator's plugins and confirm the `grok46-experiment` mode is active. Orb custom agents must be registered at plugin load, so do not call the runner until the reload has bound the uploaded prompt and its digest to that mode.

For every scenario, create exactly one inherited built-in-`high` response and one `grok46-baseline` response through the fixture runner. The `high` child receives Amp's unmodified built-in prompt and standard tools; the exact manifest bytes are its only user message. Preserve each non-empty final assistant answer verbatim in an individual Markdown file under:

```text
references/<mode>/<suite>/responses/<scenario-id>.md
references/<mode>/<suite>/records/<scenario-id>.json
```

Each record stores the source scenario hash, mode, thread ID, completion/revision checks, response path, byte count, and SHA-256 digest. Build a manifest per mode and suite. Once validated and committed, these references are immutable and reused by every generation.

Do not substitute, reconstruct, or summarize a missing final answer. An incomplete or ambiguous thread must be rerun under a new recorded thread ID before references are sealed.

## Generation lifecycle

Each generation is one fresh orb in this control project and owns one candidate prompt.

1. **Read state.** Read `state.json`, `prompts/current.json`, the current champion snapshot, all later rejected-generation metadata, and relevant files under `failures/`.
2. **Form one hypothesis.** Identify the smallest general instruction change likely to address observed failure patterns. Never put scenario IDs, Rails APIs, expected answers, judge wording, or score-specific tricks in the candidate prompt.
3. **Create an immutable candidate.** Write the next `GNNNN.md` and matching `GNNNN.json`, then point `prompts/current.json` at it and set `state.active_generation`. Never edit an existing generation pair.
4. **Validate and load.** Run `./scripts/validate-experiment.py --ready-to-run`, then reload `.amp/plugins/candidate-mode.ts` for local inspection. Verify that it names the intended generation.
5. **Run the small screen.** Create one `low` coordinator thread in `andrei/rails-for-grok-small`, upload the exact candidate prompt, reload plugins to register it as `grok46-experiment`, and invoke the fixture runner once for each small scenario. Collect five exact finals and runner records. Use one fresh `high` judge thread for blind comparison, then reveal the map only after its comparison decisions are final and ask the same thread for the separate content review.
6. **Apply the small gate.** Continue only if the candidate is preferred in at least 4 of 5 cases and the content review finds zero material candidate-only regressions. Otherwise record failures, restore `prompts/current.json` to the champion, clear `state.active_generation`, and stop this generation.
7. **Run the large suite.** Create one `low` coordinator in `andrei/rails-for-grok-large`, upload the exact candidate prompt, reload plugins to register it as `grok46-experiment`, and invoke the fixture runner once per large scenario. Judge in five independent ten-case shards. In each shard, finish and persist blind comparison decisions before revealing the map and requesting content review.
8. **Record and decide.** Persist exact responses, thread IDs, maps, judgments, evidence, and the run summary. If the large content gate passes and the candidate's preference count exceeds the champion's recorded count, promote it in `state.json`. Otherwise restore `prompts/current.json` to the existing champion.
9. **Stop or continue.** The first generation with at least 48 of 50 candidate preferences and zero candidate-only material regressions becomes `final_generation`; set `stopped: true`. There is no multi-candidate or “three passing candidates” condition. If it does not pass, write a compact failure bundle for the next generation.

A repeat run of the exact final prompt may be requested later to measure stochastic stability. It is confirmation, not a new candidate and not part of the stopping rule.

## Blind comparison

For each case, place the candidate and official-baseline responses behind labels `A` and `B`. Use a recorded run seed to assign labels deterministically and keep assignments balanced within each suite. The comparison judge receives the scenario, the fixed `high` response, and labeled `A`/`B`; it does not receive model names, generation IDs, prompt text, prior scores, or the label map.

Use `scripts/build-blind-map.py` rather than assigning labels by hand.

Ties do not count as candidate preferences. Preserve every raw final exactly. A blind judge copy may remove only transport-routing text that links to a parent or exposes a thread/mode identity, even when the agent echoed it into the terminal final. Record the source and normalized hashes plus the exact transformation, and assess the delivery behavior separately; never alter substantive answer text.

After comparison output is persisted, reveal the label map and run `judges/content-regression.md`. Content findings must cite Rails source or an executed check. Preference and correctness are separate fields and separate gates.

## Champion and failure history

`state.champion_generation` identifies the best content-safe large-suite result so far. `prompts/current.json` selects the prompt loaded by the candidate mode; it points at an active candidate during evaluation and is restored to the champion after a rejection. A later generation starts from the champion but may use lessons from every rejected generation.

This gives one serial lineage without forcing a regression to become the next parent. Immutable generation metadata records each candidate's actual parent and hypothesis.

## Outage and recovery rules

- The fixture runner writes every candidate/baseline child thread ID to `.amp/experiment-output/` immediately after creation and before it sends the scenario. Download those records from the coordinator workspace.
- If thread creation returns a connection error, treat the outcome as unknown. Reconcile direct children and records before deciding whether to retry. Never blindly create a replacement.
- A response counts only when the source thread is complete, its final answer is non-empty, the child fixture validator confirms the pinned revision, and the stored bytes match the collected final. The final prose does not need to repeat the commit hash.
- Never fabricate or substitute an answer to satisfy expected counts.
- A stopped run creates no more threads and modifies no more run artifacts.
- Do not start the next fresh generation orb until the prior generation's commit has been integrated into the control project's default branch. Fresh orbs cannot see another thread's unshipped commit.

## Artifact layout

```text
runs/GNNNN/<suite>/responses/       candidate final answers
runs/GNNNN/<suite>/records/         thread and digest records
runs/GNNNN/<suite>/blind/           seed, maps, and judge shards
runs/GNNNN/<suite>/judgments/       comparison and content outputs
runs/GNNNN/summary.json             gate and promotion decision
failures/GNNNN.json                 compact evidence for later generations
```

Store exact text in individual files. JSON files reference paths and hashes rather than embedding dozens of long answers in one manually assembled payload.
