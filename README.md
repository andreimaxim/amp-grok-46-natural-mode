# Amp Grok 4.6 Natural mode evolution

This repository is the control plane for evolving one Grok 4.6 system-prompt lineage against fixed Rails maintenance scenarios. The target is the quality of Amp's High and Ultra prompts running on the same model.

The root [`grok-46-mode.ts`](grok-46-mode.ts) is the restored official Amp Grok 4.6 plugin. Do not edit it. [`prompts/generations/G0000.md`](prompts/generations/G0000.md) is its system prompt, extracted byte-for-byte; every later generation is a small edit of the generation before it.

## How it works

1. **References, once.** For each of the 55 scenarios, one answer from the user's `grok46-high` mode and one from `grok46-ultra` (Grok 4.6 inheriting Amp's High and Ultra prompts). Collected with plain `create_thread` calls in the fixture projects; see [`prompts/bootstrap-references.md`](prompts/bootstrap-references.md).
2. **Generation 0** is the official prompt. It runs the 5-case small suite; a `high` judge decides per case whether the answer matches the references.
3. **Gates.** At least 4 of 5 small matches unlocks the 50-case large suite; at least 48 of 50 large matches ends the experiment. Anything less produces a short failure note and the next generation, which edits the previous prompt in response to that note. The large suite never runs for a generation that failed the small one.

[`PROTOCOL.md`](PROTOCOL.md) has the full rules; [`prompts/evolver.md`](prompts/evolver.md) is the instruction for running one generation.

## Fixture projects

| Suite | Repository | Amp project | Scenarios | Gate |
| --- | --- | --- | ---: | ---: |
| small | [`rails-for-grok-small`](https://github.com/andreimaxim/rails-for-grok-small) | `andrei/rails-for-grok-small` | 5 | 4 matches |
| large | [`rails-for-grok-large`](https://github.com/andreimaxim/rails-for-grok-large) | `andrei/rails-for-grok-large` | 50 | 48 matches |

Both are Rails revision `d59d106f94dcb7f8e748545c0ccf8a276d20f590` plus one commit of orb plumbing, and must look like an ordinary Rails checkout to the agents under test: nothing in them names Grok, benchmarks, or the experiment. Each carries `.amp/plugins/orb-tasks.ts`, a copy of [`harness/orb-tasks.ts`](harness/orb-tasks.ts), a generic plugin whose `run_orb_task` tool runs an uploaded agent definition (`config/official-agent.json` plus a generation prompt) against an uploaded task file in a fresh orb of that project. The scenario texts live here under [`scenarios/`](scenarios/) and are uploaded per run. `scripts/fetch-fixtures.sh` makes sparse checkouts under `.fixtures/` so the validator can confirm the fixture commit, plugin, and wording.

## Repository map

- [`experiment.json`](experiment.json): fixed configuration, gates, fixture commits.
- [`state.json`](state.json): phase and latest/active/next/final generation.
- [`prompts/generations/`](prompts/generations/): immutable prompt and metadata pairs; [`prompts/current.json`](prompts/current.json) names the latest.
- [`scenarios/small/`](scenarios/small/), [`scenarios/large/`](scenarios/large/): the scenario texts, one `<id>-<slug>.md` per case.
- [`config/official-agent.json`](config/official-agent.json): the official Grok 4.6 model, tools, effort, and compaction settings, extracted from [`grok-46-mode.ts`](grok-46-mode.ts).
- [`harness/orb-tasks.ts`](harness/orb-tasks.ts): canonical source of the generic plugin installed in both fixture repositories.
- [`judges/match.md`](judges/match.md): the per-case judge prompt.
- [`references/`](references/): reference answers, transcripts, records.
- [`runs/`](runs/): per-generation answers, transcripts, records, judgments, summary.
- [`failures/`](failures/): one short feedback note per failed generation.
- [`schemas/`](schemas/): record, judgment, summary, and generation contracts.
- [`scripts/export-thread.sh`](scripts/export-thread.sh): thread transcript export without the mode-naming front matter.
- [`.amp/plugins/candidate-mode.ts`](.amp/plugins/candidate-mode.ts): `grok46-candidate`, the latest generation as a mode for inspection in this project.

## Validation

```bash
./scripts/validate-experiment.py                 # configuration, generations, state, existing artifacts
./scripts/validate-experiment.py --ready-to-run  # also requires fixtures and the full reference corpus
```
