#!/usr/bin/env node

import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const sourcePath = join(root, 'grok-46-mode.ts')
const promptPath = join(root, 'prompts/generations/G0000.md')
const configPath = join(root, 'config/official-agent.json')
const source = await readFile(sourcePath, 'utf8')

function sha256(value) {
	return createHash('sha256').update(value).digest('hex')
}

function capture(pattern, label) {
	const match = source.match(pattern)
	if (!match) throw new Error(`Could not extract ${label} from grok-46-mode.ts`)
	return match[1]
}

const rawPrompt = capture(
	/const GROK_46_PROMPT = `([\s\S]*?)`\n\n\/\*\* Ultra's tool list/,
	'GROK_46_PROMPT',
)
if (rawPrompt.includes('${')) {
	throw new Error('GROK_46_PROMPT unexpectedly contains template interpolation')
}

const prompt = Function(`"use strict"; return \`${rawPrompt}\`;`)()
const toolsBlock = capture(
	/const ULTRA_TOOL_NAMES = \[([\s\S]*?)\] as const/,
	'ULTRA_TOOL_NAMES',
)
const tools = [...toolsBlock.matchAll(/'([^']+)'/g)].map((match) => match[1])

const config = {
	schema_version: 1,
	official_source_commit: '338c450dc6619765ae1c4a4327dabc6dd8141f4a',
	official_source_sha256: sha256(source),
	prompt_sha256: sha256(prompt),
	name: capture(/name: '([^']+)'/, 'agent name'),
	model: capture(/model: '([^']+)'/, 'model'),
	reasoning_effort: capture(/reasoningEffort: '([^']+)'/, 'reasoning effort'),
	compaction_threshold_tokens: Number(
		capture(/compactionThresholdTokens: ([\d_]+)/, 'compaction threshold').replaceAll('_', ''),
	),
	tools,
}
const serializedConfig = `${JSON.stringify(config, null, 2)}\n`

const mode = process.argv[2]
if (mode === '--write') {
	await mkdir(dirname(promptPath), { recursive: true })
	await mkdir(dirname(configPath), { recursive: true })
	await writeFile(promptPath, prompt)
	await writeFile(configPath, serializedConfig)
	console.log(`wrote ${promptPath}`)
	console.log(`wrote ${configPath}`)
} else if (mode === '--check') {
	const storedPrompt = await readFile(promptPath, 'utf8')
	const storedConfig = await readFile(configPath, 'utf8')
	if (storedPrompt !== prompt) throw new Error('G0000.md differs from the official plugin prompt')
	if (storedConfig !== serializedConfig) {
		throw new Error('official-agent.json differs from the official plugin configuration')
	}
	console.log('official baseline snapshot matches grok-46-mode.ts')
} else {
	throw new Error('Usage: extract-official-baseline.mjs --write|--check')
}
