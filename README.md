# Grok 4.6 Natural for Amp

An unofficial fork of Amp's [Grok 4.6 mode](https://ampcode.com/@amp/plugins/grok-46-mode.ts). It uses the same `xai/grok-4.6` model, Ultra system prompt, and Ultra tool set while adjusting the prompt's conversation style.

## Changes from the official mode

- Registers `grok46-natural` as **Grok 4.6 Natural**, so it can coexist with Amp's official `grok46` mode.
- Adds a prose guardrail that favors direct, natural engineer-to-engineer language. It discourages indirect predicates, fragments, stacked noun labels, slogan-like verdicts, and reflexive “X, not Y” constructions.
- Guides code explanations toward the smallest useful view: pseudocode, call trees, component trees, file trees, focused diffs, or diagrams.
- Keeps Amp's original diagram guidance, including its plain-text `diagram` blocks and Mermaid opt-in behavior.

The repository history starts with the untouched official source so each customization remains reviewable as a diff.

## Install

```sh
amp plugins add --auto-update https://raw.githubusercontent.com/andreimaxim/amp-grok-46-mode/main/grok-46-mode.ts
```

Start a thread by selecting **Grok 4.6 Natural** or by passing `--mode grok46-natural`. Installing this plugin adds a separate mode; it does not replace Amp's official Grok 4.6 mode.
