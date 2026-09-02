# References

One `grok46-high` and one `grok46-ultra` answer for each of the 55 scenarios: Grok 4.6 running Amp's High and Ultra prompts. They are the quality target every generation is judged against. They are collected once with `prompts/bootstrap-references.md` and never regenerated.

```text
references/<mode>/<suite>/<scenario-id>.md         final answer
references/<mode>/<suite>/<scenario-id>.thread.md  transcript (scripts/export-thread.sh)
references/<mode>/<suite>/<scenario-id>.json       record (schemas/response-record.schema.json)
```

`./scripts/validate-experiment.py --ready-to-run` requires the full corpus.
