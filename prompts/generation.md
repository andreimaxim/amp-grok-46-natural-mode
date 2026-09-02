# Evaluate generation <GNNNN>

You are the generation controller for `<GNNNN>` of the Grok 4.6 prompt-evolution experiment, in a fresh orb of this control repository (`andreimaxim/amp-grok-46-natural-mode`). You collect this generation's answers, have them judged, record the counts, and report. You do not interpret results, write failure notes, or touch any prompt. Do the work yourself; the only threads you create are the coordinator and judge threads described below.

Start with `git pull --ff-only`, read `PROTOCOL.md` ("Running a generation's answers" and "Judging") and `experiment.json`, then run `./scripts/fetch-fixtures.sh && ./scripts/validate-experiment.py --ready-to-run`. Stop and report if it fails. Confirm `state.json` has `latest_generation: <GNNNN>` and that `runs/<GNNNN>/summary.json` does not exist; otherwise stop and report.

## Claim the generation

Set `active_generation: "<GNNNN>"` and `phase: "evaluating"` in `state.json`, validate, commit (`git -c commit.gpgsign=false commit`), push to `origin/main`.

If `runs/<GNNNN>/` already holds answers from an earlier controller that died, keep every complete case (answer, transcript, record, and judgment if present) and collect only what is missing. Never redo a case that already counted.

## Small suite

1. Create one `medium` coordinator thread in `andrei/rails-for-grok-small` (`create_thread`, `intent: delegation`). Its first turn: confirm the `run_orb_task` tool is available. Stop if it is not.
2. With `upload_thread_file`, upload `config/official-agent.json` to the coordinator as `.amp/orb-tasks/agents/<GNNNN>.json`, the prompt `prompts/generations/<GNNNN>.md` as `.amp/orb-tasks/agents/<GNNNN>.md`, and each `scenarios/small/<id>-*.md` as `.amp/orb-tasks/tasks/<id>.md`. Ask it to reload plugins and confirm the `custom-agent` mode now names `<GNNNN>`.
3. Ask the coordinator to call `run_orb_task` once per scenario `S01`–`S05` with `task_path: .amp/orb-tasks/tasks/<id>.md` and `label: <id>`. It may run them concurrently. Do not tell the coordinator, or put in any uploaded file, what the runs are for.
4. Download each answer and record from the coordinator's `.amp/orb-tasks/output/<id>/` with `download_thread_file`, export the child thread's transcript with `scripts/export-thread.sh <thread-id> <path>`, and store answer, transcript, and record under `runs/<GNNNN>/small/` as `PROTOCOL.md` lays out (`<id>.md`, `<id>.thread.md`, `<id>.json` per `schemas/response-record.schema.json` with `generation` set and `mode` null). A run counts only when its child thread finished on its own with a non-empty answer; rerun failures as new `run_orb_task` calls and list the old thread IDs under `superseded_thread_ids`. Commit and push after all five are stored.
5. Judge the five cases in one `high` thread created in `andrei/rails-for-grok-small`, following the "Judging" section of `PROTOCOL.md` and `judges/match.md`. Store each verdict as `runs/<GNNNN>/small/<id>.judgment.json` per `schemas/judgment.schema.json`. Commit and push.

Count the `match: true` verdicts. Fewer than 4: write `runs/<GNNNN>/summary.json` (`decision: failed_small`, `large: null`) and go to "Finish".

## Large suite

Only after 4 or more small matches. Repeat the coordinator, upload, run, and collection steps in `andrei/rails-for-grok-large` for `L01`–`L50` (uploading `scenarios/large/*.md`), storing under `runs/<GNNNN>/large/`. Commit and push after every ten stored cases. Judge in five `high` threads of ten cases each, created in that project, storing each verdict as `runs/<GNNNN>/large/<id>.judgment.json`; commit and push after each batch.

Count the `match: true` verdicts. At least 48: `decision: final`. Otherwise `decision: failed_large`.

## Finish

Write `runs/<GNNNN>/summary.json` per `schemas/run-summary.schema.json` with the exact counts and thresholds from `experiment.json`. Set `active_generation: null` and `phase: "ready"` in `state.json`. Do not set `stopped`, `final_generation`, or `stop_reason`; the evolver does that. Run `./scripts/validate-experiment.py --ready-to-run`; it must pass. Commit, push to `origin/main`.

Reply with: the generation, small matches out of 5, large matches out of 50 (or "not run"), the decision, the pushed commit SHA, and any cases that needed reruns.

## Rules

- Do not run the large suite for a generation with fewer than 4 small matches.
- Do not touch `references/`, `prompts/`, or `failures/`.
- Report counts exactly as the judgments say. Never write or edit an answer or verdict yourself.
- Do not read answers or transcripts into your own context; move them as files.
- A `create_thread` call that returns a connection error has an unknown outcome: check the coordinator's `.amp/orb-tasks/output/` and its child threads before creating a replacement.
- If you cannot finish, commit and push whatever complete cases you have, leave `phase: evaluating`, and reply describing exactly where you stopped.
