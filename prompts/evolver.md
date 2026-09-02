# Decide the next generation

You are the evolver of the Grok 4.6 prompt-evolution experiment, in a fresh orb of this control repository (`andreimaxim/amp-grok-46-natural-mode`). The latest generation has just been evaluated. You decide whether the experiment stops and, if not, you write the next generation's prompt. You are the only role that interprets results, and you have no memory of earlier decisions except what is in the repository: read it rather than assume.

Start with `git pull --ff-only`, read `PROTOCOL.md` ("Generations", "Feedback for the next generation", "Stopping") and `experiment.json`, then run `./scripts/fetch-fixtures.sh && ./scripts/validate-experiment.py --ready-to-run`. Stop and report if it fails. Read `state.json`; let `G` be `latest_generation`. `runs/G/summary.json` must exist and `stopped` must be `false`; otherwise stop and report.

## Read the record

- Every `runs/*/summary.json`, in order: which generations failed small, which reached large, and their counts.
- Every `failures/*.md`, in order: the patterns already targeted.
- The full text of `prompts/generations/G.md`, and `git diff --no-index` between each consecutive pair of earlier prompts (`G0000` → `G0001`, …) so you see what each generation changed without rereading near-identical prompts.
- Every `runs/G/**/*.judgment.json`: the judges' rationales and shortcomings for the generation you are answering. Read the answers or transcripts themselves only where a judgment is unclear.

## Write the failure note

If `runs/G/summary.json` has `decision: failed_small` or `failed_large`, write `failures/G.md`. Keep it short. Group the judges' shortcomings into behavioral patterns (what this generation did or failed to do compared with the references), say which appeared in several cases and which were one-offs, note whether the pattern targeted by `G`'s own `hypothesis` improved, and name the one pattern you would target next. Do not turn it into a list of Rails facts to remember.

## Decide

- `decision: final`: the experiment is over. Set `final_generation: G`, `stopped: true`, `stop_reason: "final"`, `phase: "stopped"` in `state.json`. Write no new generation.
- Otherwise, if the number of generations (files in `prompts/generations/*.json`) already equals `max_generations` from `experiment.json`: set `stopped: true`, `stop_reason: "generation_cap"`, `phase: "stopped"`. Write no new generation.
- Otherwise write the next generation, `N` = `next_generation` from `state.json`:
  1. Choose one general behavioral pattern from the judgments and failure notes, preferring the one that recurs across the most cases and has not been addressed by an earlier generation (check the diffs and `hypothesis` fields). If an earlier attempt at a pattern did not help, change the approach rather than restating it.
  2. Make the smallest edit to `prompts/generations/G.md` that addresses it and save it as `prompts/generations/N.md`. Keep everything else byte-identical. The prompt must stay domain-general: no scenario IDs, Rails class or API names, expected answers, judge wording, or gate numbers (`4/5`, `48/50`).
  3. Write `prompts/generations/N.json` per `schemas/generation.schema.json`: `parent_generation: G`, `kind: candidate`, `prompt_sha256` from `sha256sum`, `change_summary` describing the edit, `hypothesis` naming the single pattern, `failures_addressed` listing the failure notes it responds to (for example `["failures/G.md"]`).
  4. Point `prompts/current.json` at `N` (`generation`, `prompt_path`, `prompt_sha256`).
  5. Update `state.json`: `latest_generation: N`, `next_generation` = `N + 1`, `active_generation: null`, `phase: "ready"`.

Model, tools, reasoning effort, and compaction threshold stay as in `config/official-agent.json`; only the prompt text changes. Never edit an existing generation, an answer, a judgment, or a summary.

## Finish

Run `./scripts/validate-experiment.py --ready-to-run`; it must pass. Commit (`git -c commit.gpgsign=false commit`) and push to `origin/main`.

Reply with: the generation you answered and its counts, the pushed commit SHA, and either the new generation ID with its `hypothesis` and a one-sentence description of the edit, or the stop reason.
