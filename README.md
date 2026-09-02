# Amp Grok 4.6 Natural mode evolution

This repository is the control plane for evolving one Grok 4.6 system-prompt lineage against fixed Rails maintenance scenarios.

The root [`grok-46-mode.ts`](grok-46-mode.ts) is the restored official Amp Grok 4.6 plugin baseline. Do not edit it during the experiment. Candidate prompts are immutable snapshots under [`prompts/generations/`](prompts/generations/); the repository-local `grok46-candidate` mode loads the snapshot selected by [`prompts/current.json`](prompts/current.json).

## Fixture projects

| Stage | Repository | Amp project | Scenarios | Gate |
| --- | --- | --- | ---: | ---: |
| Screen | [`rails-for-grok-small`](https://github.com/andreimaxim/rails-for-grok-small) | `andrei/rails-for-grok-small` | 5 | candidate preferred in at least 4 |
| Fitness | [`rails-for-grok-large`](https://github.com/andreimaxim/rails-for-grok-large) | `andrei/rails-for-grok-large` | 50 | candidate preferred in at least 48 |

Both fixtures pin Rails source revision `d59d106f94dcb7f8e748545c0ccf8a276d20f590`. Their scenario manifests are the source of truth; scenario text is not copied here. Scenario files contain only natural user task text. Fixture setup and validation establish the Rails revision separately, and the runner sends the exact scenario bytes without injecting experiment controls.

## Repository map

- [`PROTOCOL.md`](PROTOCOL.md): lifecycle, gates, stopping rule, and recovery rules.
- [`experiment.json`](experiment.json): machine-readable fixed configuration.
- [`prompts/evolver.md`](prompts/evolver.md): instructions for proposing and running one generation.
- [`prompts/generations/`](prompts/generations/): immutable prompt and metadata pairs. `G0000` is the exact official prompt.
- [`judges/`](judges/): blind comparison and post-decision correctness-review prompts.
- [`references/`](references/): one-time `high` and official-mode responses plus manifests.
- [`runs/`](runs/): candidate responses, blind maps, judgments, and run summaries.
- [`failures/`](failures/): compact lessons supplied to later generations.
- [`schemas/`](schemas/): artifact contracts.
- [`.amp/plugins/candidate-mode.ts`](.amp/plugins/candidate-mode.ts): project-local modes for inspecting the baseline/current candidate in this control project.
- [`harness/rails-experiment-runner.ts`](harness/rails-experiment-runner.ts): canonical runner plugin copied byte-for-byte into both Rails fixture projects. It creates candidate/baseline custom-agent orbs and inherited built-in-`high` reference orbs, sending exact scenario bytes through the child thread API without mutable global plugin state.

There is intentionally no mutable `previous-prompt.md`. A generation's `parent_generation` points to an immutable prior snapshot, while `prompts/current.json` selects the snapshot currently loaded by the candidate mode.

## Validation

```bash
./scripts/validate-experiment.py
```

To require all 55 fixed `high` and official-mode references before starting a generation:

```bash
./scripts/validate-experiment.py --ready-to-run
```

Repository setup does not create or run Generation 1.
