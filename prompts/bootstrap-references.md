# Collect the references

You are collecting the fixed reference answers for the Grok 4.6 prompt-evolution experiment: one `grok46-high` and one `grok46-ultra` answer for each of the 55 Rails scenarios. Read `PROTOCOL.md` (the "References" section) and `experiment.json` first, then run `./scripts/fetch-fixtures.sh && ./scripts/validate-experiment.py` and stop if it fails. The scenario texts are in this repository under `scenarios/small/` (`S01`–`S05`) and `scenarios/large/` (`L01`–`L50`), one `<id>-<slug>.md` file each.

For every scenario file and for each of the two modes, create one fresh thread with `create_thread`:

- `project`: `andrei/rails-for-grok-small` for `S01`–`S05`, `andrei/rails-for-grok-large` for `L01`–`L50`;
- `agent_mode`: `grok46-high` or `grok46-ultra`;
- `prompt`: the scenario file's text exactly as written, nothing before or after it;
- `intent`: `delegation`.

Run several at once; each thread is independent. Wait for them with `wait_for_threads`, then check each with `get_thread_status` or `read_thread`. A thread counts when it stopped on its own and its last assistant message is a non-empty answer to the scenario. If it errored, stalled, or ended by asking the user a question, create a new thread for that scenario and mode and list the old ID under `superseded_thread_ids`.

For each thread that counts, store under `references/<mode>/<suite>/`:

- `<scenario-id>.md`: the final assistant message, as returned, no edits;
- `<scenario-id>.thread.md`: `scripts/export-thread.sh <thread-id> <path>`;
- `<scenario-id>.json`: a record per `schemas/response-record.schema.json` with `mode` set and `generation` null.

Never write, summarize, or patch an answer yourself.

Commit in batches as you go so a lost orb does not lose finished work. When all 110 answers are stored, set `state.phase` to `ready`, run `./scripts/validate-experiment.py --ready-to-run`, commit, and push to `origin/main`. Do not create or run any generation.
