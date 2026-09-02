# Evolution protocol

## Goal

Evolve one Grok 4.6 system-prompt lineage, starting from the exact official Amp Grok 4.6 prompt, until one generation matches the quality of Amp's High and Ultra prompts running on the same model on at least 48 of the 50 large-suite Rails scenarios.

The following inputs are fixed for the whole experiment:

- Rails revision `d59d106f94dcb7f8e748545c0ccf8a276d20f590`, pinned by both fixture projects.
- Five small and fifty large natural-task scenarios, stored in this repository under `scenarios/small/` and `scenarios/large/` (one Markdown file per scenario, named `<id>-<slug>.md`).
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

Generations form one straight line. `G0000` is the official prompt, extracted byte-for-byte from `grok-46-mode.ts` and checked by `scripts/extract-official-baseline.mjs --check`. Every later generation's `parent_generation` is the immediately preceding generation, and its prompt is a small, general change to that parent's prompt motivated by the parent's judge feedback. Generation files under `prompts/generations/` are never edited after they are committed. The lineage is capped at `max_generations` (100) generations including `G0000`.

### Three roles

Three kinds of thread share the work, all in orbs of this control project, and Git is the only channel between them: every thread starts from `origin/main`, commits what it produced, pushes, and replies to the thread that spawned it. No thread relies on its own memory for facts about earlier generations; the repository is the record.

```diagram
┌──────────────────────────────────────────────────────────────┐
│ Orchestrator (medium, one long-lived thread)                 │
│ pull → read state.json → spawn the next role → wait for its  │
│ reply → repeat until state.stopped                           │
└──────────┬──────────────────────────────────┬────────────────┘
           │ "evaluate GNNNN"                 │ "GNNNN is evaluated"
           ▼                                  ▼
┌────────────────────────────┐   ┌─────────────────────────────────────┐
│ Generation controller      │   │ Evolver (ultra, fresh per gen)      │
│ (medium, fresh per gen)    │   │ reads lineage, summaries, failure   │
│ small suite (5 answers)    │   │ notes, latest judgments             │
│   → judge ─ <4 ─▶ stop     │   │ writes failures/GNNNN.md            │
│   ≥4 ▼                     │   │ then: final → stop                  │
│ large suite (50 answers)   │   │       cap reached → stop            │
│   → judge (5 batches)      │   │       otherwise → G(N+1)            │
│ writes runs/GNNNN/**       │   │ commits, pushes, replies            │
│ commits, pushes, replies   │   └─────────────────────────────────────┘
└────────────────────────────┘
```

- **Orchestrator** (`prompts/orchestrator.md`, `medium`): the thread the user starts and talks to. After each reply it runs `git pull --ff-only` and `./scripts/validate-experiment.py --ready-to-run`, reads `state.json`, and either spawns a generation controller (when `runs/<latest_generation>/summary.json` does not exist), spawns an evolver (when it does and the experiment is not stopped), or reports the stop. It edits no files and never reads answers or judgments. It waits by ending its turn; the child's reply wakes it.
- **Generation controller** (`prompts/generation.md`, `medium`): evaluates exactly one named generation. Sets `active_generation` and `phase: evaluating`, runs the small suite through the fixture runner (below), judges it, and stops there when fewer than 4 of 5 match. Otherwise runs the large suite and judges it in batches of ten. Writes `runs/<gen>/summary.json` with counts and the decision (`failed_small`, `failed_large`, or `final`), clears `active_generation`, sets `phase: ready`, commits, pushes, and replies with the counts. It interprets nothing and writes no failure note or prompt. If it finds answers for its generation already committed (a previous controller died), it keeps them and collects only what is missing.
- **Evolver** (`prompts/evolver.md`, `ultra`): runs once per evaluated generation with a fresh context. Reads `state.json`, all `runs/*/summary.json`, all `failures/*.md`, the latest prompt in full, the diff between each consecutive pair of earlier prompts, and the latest generation's `*.judgment.json` files. If the latest decision is a failure it writes `failures/<gen>.md`. Then: `decision: final` → set `final_generation`, `stopped: true`, `stop_reason: final`, `phase: stopped`. Lineage already at `max_generations` → `stopped: true`, `stop_reason: generation_cap`, `phase: stopped`. Otherwise write the next `GNNNN.md` and `GNNNN.json` (`parent_generation` = the latest, `kind: candidate`, `hypothesis` names the single pattern targeted), point `prompts/current.json` at it, set `latest_generation`/`next_generation`, `phase: ready`. Commit, push, reply with the hypothesis or the stop reason.

Every hand-off is validated: `./scripts/validate-experiment.py --ready-to-run` must pass before each commit, and the orchestrator runs it after each pull.

### Running a generation's answers

Project-local modes do not travel between Amp projects, so the fixture projects carry a generic plugin, `.amp/plugins/orb-tasks.ts` (a copy of `harness/orb-tasks.ts`). The fixture repositories must look like an ordinary Rails checkout to the agents under test: one commit on top of the Rails revision that adds only orb plumbing (`.agents/setup`, the plugin, empty `.amp/orb-tasks/{agents,tasks,output}/` directories, `mise.toml`), with no wording about Grok, benchmarks, or experiments anywhere. Scenarios and the agent configuration live in this repository and are uploaded per run; nothing in a fixture names the experiment. `scripts/validate-experiment.py` checks all of this against `experiment.json`.

The plugin loads exactly one agent from `.amp/orb-tasks/agents/<name>.json` (model, reasoning effort, compaction threshold, tools: the contents of `config/official-agent.json`) plus `<name>.md` (the system prompt), and exposes a `run_orb_task` tool that creates a fresh child orb in the fixture project running that agent, sends the contents of a task file under `.amp/orb-tasks/tasks/` verbatim as the first message, and stores the child thread ID and final answer under `.amp/orb-tasks/output/<label>/<thread-id>.md|.json`.

For each suite:

1. Create one `medium` coordinator thread in the suite's Amp project. Its first turn confirms the `run_orb_task` tool is available.
2. Upload `config/official-agent.json` to the coordinator as `.amp/orb-tasks/agents/<GNNNN>.json` and the generation's prompt file as `.amp/orb-tasks/agents/<GNNNN>.md`; upload every scenario file of the suite to `.amp/orb-tasks/tasks/<scenario-id>.md`. Ask the coordinator to reload its plugins and confirm the `custom-agent` mode now names `<GNNNN>`.
3. Ask the coordinator to call `run_orb_task` once per scenario with `task_path: .amp/orb-tasks/tasks/<scenario-id>.md` and `label: <scenario-id>`. It may run them concurrently.
4. Download each answer and record from `.amp/orb-tasks/output/<scenario-id>/`. Export the child thread's transcript with `scripts/export-thread.sh`. Store:

```text
runs/<gen>/<suite>/<scenario-id>.md          final answer
runs/<gen>/<suite>/<scenario-id>.thread.md   transcript
runs/<gen>/<suite>/<scenario-id>.json        record: thread ID, generation, suite, scenario
runs/<gen>/<suite>/<scenario-id>.judgment.json
runs/<gen>/summary.json
```

The same completeness rule applies as for references: a run counts only when its thread finished on its own with a non-empty answer. A thread creation that returns a connection error has an unknown outcome; look at the coordinator's `.amp/orb-tasks/output/` records and its child threads before creating a replacement.

## Judging

One case at a time, in a `high` judge thread created in the suite's Amp project so it can verify claims against the pinned Rails checkout. Its first turn is `judges/match.md` plus `mkdir -p .amp/judge-inputs`; then upload each case's files (scenario, `R1`/`R2` answers and transcripts, `X` answer and transcript) under `.amp/judge-inputs/<scenario-id>/` and ask for that case's verdict. The judge is not told the generation, the prompt, the modes, or any earlier result; transcripts are exported with `scripts/export-thread.sh`, which removes the front matter that names the mode. Alternate which reference is `R1` between cases.

The judge returns one JSON object per case conforming to `schemas/judgment.schema.json`: `match` (true or false), a rationale, and a list of concrete shortcomings relative to the references. A case matches when the evaluated answer serves the user at least as well as the references on correctness, investigation and verification, autonomy, and communication, and has no material error the references avoid. The judge must verify disputed factual claims in the Rails checkout rather than trusting either side.

Use one judge thread for the small suite and one per batch of ten for the large suite. Count `match: true` cases; nothing else counts.

## Feedback for the next generation

`failures/<gen>.md` is a short note, written by the evolver after it reads the generation's judgments, that distills the judge's shortcomings into general patterns of behavior: what the generation did that the references did not, and vice versa. It should not mention scenario IDs or Rails APIs as things to remember; the next prompt must stay domain-general. The next generation's `hypothesis` names the single pattern it targets.

A candidate prompt must never contain scenario IDs, Rails class or API names, expected answers, the judge's wording, or the gate numbers.

## Stopping

The experiment stops at the first generation with at least 48 of 50 large-suite matches (`stop_reason: final`), or when `max_generations` generations have been evaluated without one (`stop_reason: generation_cap`). There is no champion, no promotion, and no multi-candidate condition: the lineage is linear and the last generation is always the parent of the next.

## Artifact layout

```text
prompts/generations/GNNNN.md, GNNNN.json   immutable prompt and metadata
prompts/current.json                        the latest generation
references/<mode>/<suite>/                  reference answers, transcripts, records
runs/GNNNN/<suite>/                         generation answers, transcripts, records, judgments
runs/GNNNN/summary.json                     counts and decision
failures/GNNNN.md                           feedback for the next generation
state.json                                  phase, latest/active/next/final generation, stop reason
```
