# Evaluate one generation

You own one generation of the Grok 4.6 prompt-evolution experiment, in a fresh orb of this control repository. Read `PROTOCOL.md` and `experiment.json`, then run `./scripts/validate-experiment.py --ready-to-run`; stop if it fails.

## Which generation

Read `state.json`. If `runs/<latest_generation>/summary.json` does not exist, that generation has not been evaluated yet: evaluate it. This is how `G0000`, the official prompt, gets its own run.

Otherwise create the next generation. Read the latest generation's prompt, its `runs/<gen>/summary.json`, its judgments, and `failures/<gen>.md`, plus earlier failure notes. Choose one general behavioral pattern the judges kept flagging and make the smallest change to the latest prompt that addresses it. Write `prompts/generations/<next>.md` and `<next>.json` (`parent_generation` = the latest generation, `kind: candidate`, `hypothesis` names the pattern), compute the prompt's SHA-256 with `sha256sum` for the metadata and `prompts/current.json`, and update `state.json` (`latest_generation`, `next_generation`, `active_generation`, `phase: evaluating`). Never edit an existing generation. The prompt must stay domain-general: no scenario IDs, Rails class or API names, expected answers, judge wording, or gate numbers. Model, tools, effort, and compaction threshold stay as in `config/official-agent.json`.

## Small suite

1. Create one `low` coordinator thread in `andrei/rails-for-grok-small`. Its first turn: confirm the `run_orb_task` tool is available. Stop if it is not.
2. With `upload_thread_file`, upload `config/official-agent.json` to the coordinator as `.amp/orb-tasks/agents/<gen>.json`, the generation's prompt `prompts/generations/<gen>.md` as `.amp/orb-tasks/agents/<gen>.md`, and each `scenarios/small/<id>-*.md` as `.amp/orb-tasks/tasks/<id>.md`. Ask it to reload plugins and confirm the `custom-agent` mode now names `<gen>`.
3. Ask the coordinator to call `run_orb_task` once per scenario `S01`–`S05` with `task_path: .amp/orb-tasks/tasks/<id>.md` and `label: <id>`. It may run them concurrently. Do not tell the coordinator, or put in any uploaded file, what the runs are for.
4. Download each answer and record from the coordinator's `.amp/orb-tasks/output/<id>/`, export the child thread's transcript with `scripts/export-thread.sh`, and store answer, transcript, and record under `runs/<gen>/small/` as `PROTOCOL.md` lays out. A run counts only when its thread finished with a non-empty answer; rerun failures as new threads.
5. Judge the five cases in one `high` thread created in `andrei/rails-for-grok-small`, following the "Judging" section of `PROTOCOL.md` and `judges/match.md`. Store each verdict as `runs/<gen>/small/<scenario-id>.judgment.json`.

Fewer than 4 matches: write `runs/<gen>/summary.json` (`decision: failed_small`, `large: null`) and `failures/<gen>.md`, clear `active_generation`, set `phase: ready`, validate, commit, push to `origin/main`, and stop.

## Large suite

Only after 4 or more small matches. Repeat the coordinator, upload, run, and collection steps in `andrei/rails-for-grok-large` for `L01`–`L50` (uploading `scenarios/large/*.md`), storing under `runs/<gen>/large/`. Judge in five `high` threads of ten cases each, created in that project.

At least 48 matches: `decision: final`, set `final_generation`, `stopped: true`, `phase: stopped`. Otherwise `decision: failed_large` and `failures/<gen>.md`. Either way clear `active_generation`, validate, commit, and push.

## Writing the failure note

`failures/<gen>.md` is short. Group the judges' shortcomings into behavioral patterns (what this generation did or failed to do compared with the references), say which appeared in several cases and which were one-offs, and name the one pattern you would target next. Do not turn it into a list of Rails facts to remember.

## Rules

- Do not run the large suite for a generation that has not passed the small suite.
- Do not touch the reference corpus.
- Report counts exactly as the judgments say. Never write or edit an answer or verdict yourself.
- Everything for this generation must be committed and pushed before another generation starts; the next orb only sees `origin/main`.
