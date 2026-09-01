import type { PluginAPI } from '@ampcode/plugin'
import { createHash } from 'node:crypto'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { isAbsolute, join, relative, resolve, sep } from 'node:path'

export const description =
	'Runs one benchmark scenario in a fresh orb with an uploaded Grok 4.6 experiment prompt.'

const RAILS_REVISION = 'd59d106f94dcb7f8e748545c0ccf8a276d20f590'
const AGENT_CONFIG_SHA256 =
	'489706fee404c26d60edd234490a0a8e67630c8db547b6a98ffc4b1f6da93d7d'

type AgentConfig = {
	model: `${string}/${string}`
	reasoning_effort: 'high'
	compaction_threshold_tokens: number
	tools: string[]
}

function sha256(value: Uint8Array | string) {
	return createHash('sha256').update(value).digest('hex')
}

function stringInput(input: Record<string, unknown>, name: string) {
	const value = input[name]
	if (typeof value !== 'string' || !value) throw new Error(`${name} is required`)
	return value
}

function pathWithin(root: string, directory: string, path: string) {
	if (isAbsolute(path)) throw new Error('paths must be workspace-relative')
	const boundary = resolve(root, directory)
	const candidate = resolve(root, path)
	if (candidate !== boundary && !candidate.startsWith(`${boundary}${sep}`)) {
		throw new Error(`${path} must be under ${directory}`)
	}
	return candidate
}

export default function (amp: PluginAPI) {
	const workspaceRoot = amp.system.workspaceRoot
	if (!workspaceRoot) throw new Error('The experiment runner requires a workspace')
	const root = amp.helpers.filePathFromURI(workspaceRoot)
	const configPath = join(root, 'benchmark/official-agent.json')
	const configBytes = readFileSync(configPath)
	if (sha256(configBytes) !== AGENT_CONFIG_SHA256) {
		throw new Error('benchmark/official-agent.json differs from the fixed experiment configuration')
	}
	const config = JSON.parse(configBytes.toString()) as AgentConfig

	amp.registerTool({
		name: 'run_grok46_experiment_case',
		title: 'Run Grok 4.6 experiment case',
		description:
			'Run one scenario from benchmark/suite.json in a fresh child orb with an uploaded immutable experiment prompt. Returns the child thread ID and exact-output paths.',
		inputSchema: {
			type: 'object',
			properties: {
				generation: {
					type: 'string',
					description: 'Generation ID, such as G0000 or G0001.',
				},
				mode: {
					type: 'string',
					description: 'Either grok46-baseline or grok46-candidate.',
				},
				scenario_id: {
					type: 'string',
					description: 'Scenario ID from benchmark/suite.json.',
				},
				instructions_path: {
					type: 'string',
					description: 'Workspace-relative prompt path under .amp/experiment-inputs/.',
				},
				instructions_sha256: {
					type: 'string',
					description: 'Expected SHA-256 of the exact prompt bytes.',
				},
			},
			required: [
				'generation',
				'mode',
				'scenario_id',
				'instructions_path',
				'instructions_sha256',
			],
		},
		async execute(input, ctx) {
			const generation = stringInput(input, 'generation')
			const mode = stringInput(input, 'mode')
			const scenarioID = stringInput(input, 'scenario_id')
			const instructionsPath = stringInput(input, 'instructions_path')
			const expectedInstructionsHash = stringInput(input, 'instructions_sha256')
			if (!/^G\d{4}$/.test(generation)) throw new Error('invalid generation ID')
			if (!['grok46-baseline', 'grok46-candidate'].includes(mode)) {
				throw new Error('invalid experiment mode')
			}
			if ((mode === 'grok46-baseline') !== (generation === 'G0000')) {
				throw new Error('G0000 must be baseline and later generations must be candidates')
			}
			if (!/^[SL]\d{2}$/.test(scenarioID)) throw new Error('invalid scenario ID')

			const promptPath = pathWithin(root, '.amp/experiment-inputs', instructionsPath)
			const instructions = readFileSync(promptPath)
			if (sha256(instructions) !== expectedInstructionsHash) {
				throw new Error('uploaded prompt digest mismatch')
			}
			const suite = JSON.parse(readFileSync(join(root, 'benchmark/suite.json'), 'utf8'))
			const scenario = suite.scenarios.find(
				(entry: { id?: string }) => entry.id === scenarioID,
			)
			if (!scenario) throw new Error(`${scenarioID} is not in benchmark/suite.json`)
			const scenarioPath = pathWithin(root, 'benchmark/scenarios', scenario.path)
			const scenarioBytes = readFileSync(scenarioPath)
			if (sha256(scenarioBytes) !== scenario.sha256) {
				throw new Error(`${scenarioID} scenario digest mismatch`)
			}

			const agent = amp.createAgent({
				name: 'Grok 4.6',
				model: config.model,
				instructions: instructions.toString(),
				tools: config.tools,
				reasoningEffort: config.reasoning_effort,
				compactionThresholdTokens: config.compaction_threshold_tokens,
				display: { label: `${mode === 'grok46-baseline' ? 'base' : 'candidate'}-${generation}` },
			})
			const child = await agent.createThread({
				parentThreadID: ctx.thread.id,
				executor: 'orb',
			})
			const outputDirectory = join(
				root,
				'.amp/experiment-output',
				generation,
				scenarioID,
			)
			const responsePath = join(outputDirectory, `${child.id}.md`)
			const recordPath = join(outputDirectory, `${child.id}.json`)
			mkdirSync(outputDirectory, { recursive: true })
			const record = {
				schema_version: 1,
				generation,
				mode,
				scenario_id: scenarioID,
				scenario_path: scenario.path,
				scenario_sha256: scenario.sha256,
				thread_id: child.id,
				rails_revision: RAILS_REVISION,
				instructions_sha256: expectedInstructionsHash,
				status: 'running',
			}
			writeFileSync(recordPath, `${JSON.stringify(record, null, 2)}\n`)

			try {
				await child.append([
					{ type: 'user-message', content: scenarioBytes.toString() },
				])
				const response = await child.waitForResponse({ timeoutMs: 30 * 60 * 1000 })
				const finalAnswer = response.content
					.filter((block) => block.type === 'text')
					.map((block) => block.text)
					.join('')
				if (!finalAnswer) throw new Error('child returned an empty final answer')
				writeFileSync(responsePath, finalAnswer)
				const completed = {
					...record,
					status: 'completed',
					completed: true,
					revision_ok: true,
					final_answer_path: relative(root, responsePath),
					final_answer_sha256: sha256(finalAnswer),
					final_answer_bytes: Buffer.byteLength(finalAnswer),
				}
				writeFileSync(recordPath, `${JSON.stringify(completed, null, 2)}\n`)
				return JSON.stringify({
					status: completed.status,
					thread_id: completed.thread_id,
					record_path: relative(root, recordPath),
					final_answer_path: completed.final_answer_path,
				})
			} catch (error) {
				const failed = {
					...record,
					status: 'error',
					error: error instanceof Error ? error.message : String(error),
				}
				writeFileSync(recordPath, `${JSON.stringify(failed, null, 2)}\n`)
				return JSON.stringify({
					status: failed.status,
					thread_id: failed.thread_id,
					record_path: relative(root, recordPath),
					error: failed.error,
				})
			}
		},
	})
}
