// @amp-agent-mode {"key":"grok46-baseline","label":"grok46-baseline"}
// @amp-agent-mode {"key":"grok46-candidate","label":"grok46-candidate"}

import type { PluginAPI } from '@ampcode/plugin'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

export const description =
	'Provides immutable official-baseline and current-candidate Grok 4.6 modes for the prompt evolution experiment.'

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
	if (!workspaceRoot) throw new Error('Experiment agent modes require a workspace')
	const root = amp.helpers.filePathFromURI(workspaceRoot)
	const current = JSON.parse(
		readFileSync(join(root, 'prompts/current.json'), 'utf8'),
	) as CurrentPrompt
	const config = JSON.parse(
		readFileSync(join(root, 'config/official-agent.json'), 'utf8'),
	) as OfficialAgent
	const instructions = readFileSync(join(root, current.prompt_path), 'utf8')
	const baselineInstructions = readFileSync(
		join(root, 'prompts/generations/G0000.md'),
		'utf8',
	)
	const actualHash = createHash('sha256').update(instructions).digest('hex')

	if (actualHash !== current.prompt_sha256) {
		throw new Error(
			`Candidate prompt hash mismatch for ${current.generation}: expected ${current.prompt_sha256}, got ${actualHash}`,
		)
	}

	const sharedAgentConfig = {
		name: 'Grok 4.6',
		model: config.model,
		tools: config.tools,
		reasoningEffort: config.reasoning_effort,
		compactionThresholdTokens: config.compaction_threshold_tokens,
	}
	const baseline = amp.createAgent({
		...sharedAgentConfig,
		instructions: baselineInstructions,
		display: { label: 'grok46-baseline' },
	})
	const candidate = amp.createAgent({
		...sharedAgentConfig,
		instructions,
		display: { label: 'grok46-candidate' },
	})

	amp.registerAgentMode({
		key: 'grok46-baseline',
		description:
			'Runs the immutable official Grok 4.6 baseline. Use only to build or audit the fixed experiment references.',
		agent: baseline.definition,
	})
	amp.registerAgentMode({
		key: 'grok46-candidate',
		description: `Runs experiment candidate ${current.generation}. Use for this generation's fresh scenario responses.`,
		agent: candidate.definition,
	})
}
