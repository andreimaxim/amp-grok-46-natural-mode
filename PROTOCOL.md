# Evolution protocol

## Goal

Evolve one Grok 4.6 system-prompt lineage, starting from the exact official Amp Grok 4.6 prompt, until one generation matches the quality of Amp's High and Ultra prompts running on the same model on at least 48 of the 50 large-suite Rails scenarios.

The following inputs are fixed for the whole experiment:

- Rails revision `d59d106f94dcb7f8e748545c0ccf8a276d20f590`, pinned by both fixture projects.
- Five small and fifty large natural-task scenarios, owned by the fixture projects' `benchmark/suite.json` manifests.
- One `grok46-high` and one `grok46-ultra` response per scenario (the references).
- Model, tools, reasoning effort, and compaction threshold from `config/official-agent.json`. Only the system prompt evolves.
- The judge prompt and gates in this repository.

## The two funnels

```diagram
References (once)                     Generations (repeat until stop)
┌──────────────────────────┐          ┌──────────────────────────────────┐
│ 55 scenarios             │          │ G0000 = official prompt          │
│  × grok46-high  → answer │          │ G(n+1) = small edit of G(n)      │
│  × grok46-ultra → answer │          └───────────────┬──────────────────┘
└─────────────┬────────────┘                          │
              │                                       ▼
              │                       ┌──────────────────────────────────┐
              │                       │ small suite: 5 answers           │
              │                       │ judge: match references? ≥ 4/5   │
              │                       └──────┬─────────────────┬─────────┘
              │                          fail│             pass│
              │                              ▼                 ▼
              │                     next generation   ┌──────────────────────────────┐
              │                                       │ large suite: 50 answers      │
              └──────────────────────────────────────▶│ judge: match? ≥ 48/50 → STOP │
                                                      │ otherwise → next generation  │
                                                      └──────────────────────────────┘
```

The large suite runs only for a generation that passed the small suite.

## References

`grok46-high` and `grok46-ultra` are the user's custom modes: Grok 4.6 at high reasoning effort inheriting Amp's built-in High and Ultra prompts and tools. They are the quality target. They are collected once, before Generation 0, and never regenerated.

For each scenario, create one fresh thread per reference mode directly with `create_thread`:

- `project`: the suite's Amp project (`andrei/rails-for-grok-small` or `andrei/rails-for-grok-large`);
- `agent_mode`: `grok46-high` or `grok46-ultra`;
- `prompt`: the scenario file's text, unchanged, with nothing added.

When the thread is idle, store its final assistant answer and its full transcript:

```text
references/<mode>/<suite>/<scenario-id>.md         final answer
references/<mode>/<suite>/<scenario-id>.thread.md  transcript from scripts/export-thread.sh
references/<mode>/<suite>/<scenario-id>.json       record: thread ID, mode, suite, scenario
```

A response counts when the thread finished on its own and its final answer is non-empty. A thread that errored, stalled, or ended by asking a question instead of answering is rerun as a new thread; the record keeps the ID of the thread that counted. Never write, summarize, or patch an answer by hand.

The bootstrap is complete when all 110 answers (55 scenarios × 2 modes) exist with their records and transcripts and `./scripts/validate-experiment.py --ready-to-run` passes. Commit and push it; then set `state.phase` to `ready`.

## Generations

Generations form one straight line. `G0000` is the official prompt, extracted byte-for-byte from `grok-46-mode.ts` and checked by `scripts/extract-official-baseline.mjs --check`. Every later generation's `parent_generation` is the immediately preceding generation, and its prompt is a small, general change to that parent's prompt motivated by the parent's judge feedback. Generation files under `prompts/generations/` are never edited after they are committed.

Each generation is evaluated in one fresh orb of this control project:

1. **Read state.** Read `state.json`, `experiment.json`, the latest generation's prompt and metadata, and `runs/*/summary.json` and `failures/*.md` for all earlier generations.
2. **Pick the generation to evaluate.** If `runs/<latest_generation>/summary.json` does not exist, evaluate `latest_generation` itself (this is how `G0000` runs). Otherwise write the next `GNNNN.md` and `GNNNN.json` with `parent_generation` = `latest_generation`, point `prompts/current.json` at it, and set it as `latest_generation`. Set `active_generation` and `phase: evaluating`.
3. **Validate.** `./scripts/validate-experiment.py --ready-to-run`.
4. **Run the small suite.** Collect five answers through the fixture runner (below). Judge them. Fewer than 4 of 5 matches: write `runs/<gen>/summary.json` with `decision: failed_small`, write `failures/<gen>.md`, clear `active_generation`, commit, push, stop.
5. **Run the large suite.** Collect fifty answers and judge them in batches of ten. At least 48 of 50 matches: `decision: final`, set `final_generation`, `stopped: true`, `phase: stopped`. Otherwise `decision: failed_large` and a failure note.
6. **Commit and push** the whole generation (prompt, metadata, answers, transcripts, records, judgments, summary, failure note, state) before any other generation starts. Fresh orbs only see what is on `origin/main`.

### Running a generation's answers

Project-local modes do not travel between Amp projects, so the fixture projects carry `.amp/plugins/experiment-runner.ts` (a copy of `harness/rails-experiment-runner.ts`). Its `run_grok46_experiment_case` tool creates a fresh child orb in the fixture project whose agent runs an uploaded prompt with the fixed official configuration, sends the scenario from the fixture's own manifest, and stores the child thread ID and final answer under `.amp/experiment-output/`.

For each suite:

1. Create one `low` coordinator thread in the suite's Amp project. Its first turn runs `benchmark/bin/validate` and confirms `run_grok46_experiment_case` is available.
2. Upload the generation's prompt file to the coordinator at `.amp/experiment-inputs/<GNNNN>.md`, reload its plugins, and confirm the `grok46-experiment` mode now names that generation. The tool also wants the prompt's SHA-256; compute it with `sha256sum` and pass it along.
3. Ask the coordinator to call the tool once per scenario with `generation`, `mode` (`grok46-baseline` for `G0000`, `grok46-candidate` for all later generations), `scenario_id`, `instructions_path`, and `instructions_sha256`.
4. Download each answer and record. Export the child thread's transcript with `scripts/export-thread.sh`. Store:

```text
runs/<gen>/<suite>/<scenario-id>.md          final answer
runs/<gen>/<suite>/<scenario-id>.thread.md   transcript
runs/<gen>/<suite>/<scenario-id>.json        record: thread ID, generation, suite, scenario
runs/<gen>/<suite>/<scenario-id>.judgment.json
runs/<gen>/summary.json
```

The same completeness rule applies as for references: a run counts only when its thread finished on its own with a non-empty answer. A thread creation that returns a connection error has an unknown outcome; look at the coordinator's `.amp/experiment-output/` records and its child threads before creating a replacement.

## Judging

One case at a time, in a `high` judge thread created in the suite's Amp project so it can verify claims against the pinned Rails checkout. Its first turn is `judges/match.md` plus `mkdir -p .amp/judge-inputs`; then upload each case's files (scenario, `R1`/`R2` answers and transcripts, `X` answer and transcript) under `.amp/judge-inputs/<scenario-id>/` and ask for that case's verdict. The judge is not told the generation, the prompt, the modes, or any earlier result; transcripts are exported with `scripts/export-thread.sh`, which removes the front matter that names the mode. Alternate which reference is `R1` between cases.

The judge returns one JSON object per case conforming to `schemas/judgment.schema.json`: `match` (true or false), a rationale, and a list of concrete shortcomings relative to the references. A case matches when the evaluated answer serves the user at least as well as the references on correctness, investigation and verification, autonomy, and communication, and has no material error the references avoid. The judge must verify disputed factual claims in the Rails checkout rather than trusting either side.

Use one judge thread for the small suite and one per batch of ten for the large suite. Count `match: true` cases; nothing else counts.

## Feedback for the next generation

`failures/<gen>.md` is a short note, written after the summary, that distills the judge's shortcomings into general patterns of behavior: what the generation did that the references did not, and vice versa. It should not mention scenario IDs or Rails APIs as things to remember; the next prompt must stay domain-general. The next generation's `hypothesis` names the single pattern it targets.

A candidate prompt must never contain scenario IDs, Rails class or API names, expected answers, the judge's wording, or the gate numbers.

## Stopping

The experiment stops at the first generation with at least 48 of 50 large-suite matches. There is no champion, no promotion, and no multi-candidate condition: the lineage is linear and the last generation is always the parent of the next.

## Artifact layout

```text
prompts/generations/GNNNN.md, GNNNN.json   immutable prompt and metadata
prompts/current.json                        the latest generation
references/<mode>/<suite>/                  reference answers, transcripts, records
runs/GNNNN/<suite>/                         generation answers, transcripts, records, judgments
runs/GNNNN/summary.json                     counts and decision
failures/GNNNN.md                           feedback for the next generation
state.json                                  phase, latest/active/next/final generation
```
