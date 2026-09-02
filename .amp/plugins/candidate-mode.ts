// @amp-agent-mode {"key":"grok46-candidate","label":"grok46-candidate"}

import type { PluginAPI } from '@ampcode/plugin'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

export const description =
	'Runs the latest Grok 4.6 generation prompt from prompts/current.json for local inspection in the control repository.'

type CurrentPrompt = {
	generation: string
	prompt_path: string
	prompt_sha256: string
}

type OfficialAgent = {
	model: `${string}/${string}`
	reasoning_effort: 'high'
	compaction_threshold_tokens: number
	tools: string[]
}

export default function (amp: PluginAPI) {
	const workspaceRoot = amp.system.workspaceRoot
	if (!workspaceRoot) throw new Error('The candidate mode requires a workspace')
	const root = amp.helpers.filePathFromURI(workspaceRoot)
	const current = JSON.parse(
		readFileSync(join(root, 'prompts/current.json'), 'utf8'),
	) as CurrentPrompt
	const config = JSON.parse(
		readFileSync(join(root, 'config/official-agent.json'), 'utf8'),
	) as OfficialAgent
	const instructions = readFileSync(join(root, current.prompt_path), 'utf8')
	const actualHash = createHash('sha256').update(instructions).digest('hex')
	if (actualHash !== current.prompt_sha256) {
		throw new Error(
			`${current.generation} prompt was edited after prompts/current.json recorded it`,
		)
	}

	const candidate = amp.createAgent({
		name: 'Grok 4.6',
		model: config.model,
		tools: config.tools,
		reasoningEffort: config.reasoning_effort,
		compactionThresholdTokens: config.compaction_threshold_tokens,
		instructions,
		display: { label: `grok46-candidate ${current.generation}` },
	})

	amp.registerAgentMode({
		key: 'grok46-candidate',
		description: `Runs generation ${current.generation} with the official Grok 4.6 model, tools, and effort.`,
		agent: candidate.definition,
	})
}
