# Fixed references

`high` and `grok46-baseline` responses are generated once for all 55 scenarios and reused unchanged. Each final answer lives in its own Markdown file; JSON records and manifests bind it to the source scenario, thread, mode, revision, byte count, and SHA-256 digest.

The corpus is intentionally absent from repository setup. Generate it with `prompts/bootstrap-references.md`, then require it with `./scripts/validate-experiment.py --ready-to-run` before Generation 1.
