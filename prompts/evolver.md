# Run one prompt generation

You own exactly one generation of the Grok 4.6 natural-mode evolution experiment. Work in a fresh orb for this control repository. Do the work yourself except for the explicitly required response and judge threads. Do not start another generation.

Follow `PROTOCOL.md` and `experiment.json` exactly. First run `./scripts/validate-experiment.py --ready-to-run`. Read the current champion prompt and metadata, all later generation metadata, run summaries, and failure bundles. Treat scenario answers and judge conclusions as evidence about general agent behavior, not text to memorize.

Create one candidate with the next unused `GNNNN` identifier. Make the smallest coherent system-prompt change that tests one explicit hypothesis. The candidate must remain domain-general. It must not contain scenario IDs, Rails class/API names, expected case-specific facts, copied reference phrases, numeric target scores, or instructions to game the judge. Keep the official model, tool list, reasoning effort, and compaction threshold unchanged.

Write the immutable prompt and generation metadata, update `prompts/current.json` and `state.json`, validate, and reload `.amp/plugins/candidate-mode.ts` for local inspection. Create one `low` coordinator in the small Rails project; its first turn must run the fixture validator and confirm `run_grok46_experiment_case` is available. Upload the candidate prompt byte-for-byte to `.amp/experiment-inputs/<generation>.md` and preserve its digest. Stop before collection if the preflight or upload fails; never paste the system prompt into a user message as a fallback.

Run the small screen first by asking the coordinator to invoke `run_grok46_experiment_case` once per scenario with the active generation, mode `grok46-candidate`, scenario ID, uploaded prompt path, and digest. Download all exact outputs and records, then create one blind `high` judge thread. Persist the judge's comparison output before revealing the map; then use the same judge thread and `judges/content-regression.md` for the separate content review. Do not run the large suite unless both small gates pass.

If the small gates pass, repeat the coordinator preflight/upload in the large Rails project and invoke the runner once for each of the fifty scenarios. Judge five ten-case shards independently. Lock each shard's blind decisions before revealing its map and requesting the content review.

The fixture runner reads exact scenario bytes from its validated manifest and records child IDs before starting each turn. Download its records and outputs; reconcile unknown outcomes there before retries. Preserve every final answer byte-for-byte in an individual control-repository file with a digest record. Do not replace missing data or claim validation you did not perform. Build deterministic balanced A/B assignments with `scripts/build-blind-map.py`.

Apply the promotion and stopping rules mechanically. Persist the run summary and a concise failure bundle that distinguishes broad instruction problems from case-specific noise. Restore `prompts/current.json` to the champion after a rejection. On success, point it at the promoted/final generation. Run repository validation and commit the complete generation locally. Do not push.
