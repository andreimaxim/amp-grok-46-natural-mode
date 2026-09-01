# Bootstrap the fixed response corpus

You are creating the one-time fixed reference corpus for the Grok 4.6 natural-mode evolution experiment. Do this work yourself; the response threads described below are the explicitly authorized delegation.

Read `experiment.json`, `PROTOCOL.md`, both `.fixtures/<suite>/benchmark/suite.json` manifests, and the response-record schema before acting. Confirm the fixture hashes locally. In each target Rails project, create one `high` coordinator whose first turn only runs `benchmark/bin/validate` and confirms that `run_grok46_experiment_case` is available. Stop without creating response threads if either preflight fails.

Upload `prompts/generations/G0000.md` byte-for-byte to `.amp/experiment-inputs/G0000.md` in both coordinator workspaces and retain its SHA-256. The parent directory is tracked and already exists.

For each of the 55 scenarios:

1. Read the exact scenario bytes from the verified sparse checkout. Create one fresh direct thread in the scenario's fixture project using mode `high` and those bytes as the complete initial user request.
2. Ask the suite coordinator to call `run_grok46_experiment_case` with generation `G0000`, mode `grok46-baseline`, the scenario ID, uploaded prompt path, and exact prompt digest. The runner reads and verifies the scenario itself.
3. Preserve the direct high thread ID and download the runner's child record/output before continuing. The runner makes its child ID durable before the child turn starts.
4. Collect the exact, non-empty final assistant answer. Confirm the thread completed and its fixture validator established Rails revision `d59d106f94dcb7f8e748545c0ccf8a276d20f590`; the answer itself need not repeat the hash.
5. Store the final under `references/<mode>/<suite>/responses/<scenario-id>.md` and its metadata under `records/<scenario-id>.json`.

Creation failures have unknown outcomes. Reconcile direct children and existing records before retrying. Never invent, summarize, or substitute final text.

Build manifests containing sorted scenario IDs, scenario hashes, response paths and hashes, mode, and thread IDs. Validate 55 unique scenarios per mode across the two suites, exact expected counts, non-empty response files, unique generation thread IDs, all completion/revision flags true, and matching SHA-256 digests.

When complete, change `state.phase` from `bootstrap_references` to `ready`, run `./scripts/validate-experiment.py --ready-to-run`, and commit the reference corpus locally. Do not create Generation 1 and do not push.
