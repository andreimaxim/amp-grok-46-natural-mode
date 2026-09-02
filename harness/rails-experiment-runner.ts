// @amp-agent-mode {"key":"grok46-experiment","label":"grok46-experiment"}
// @amp-agent-mode {"key":"grok46-reference-high","label":"grok46-reference-high"}

import type { PluginAPI } from '@ampcode/plugin'
import { createHash } from 'node:crypto'
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
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

function delay(milliseconds: number) {
	return new Promise((resolve) => setTimeout(resolve, milliseconds))
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
	const inputDirectory = join(root, '.amp/experiment-inputs')
	const promptFiles = readdirSync(inputDirectory)
		.filter((path) => /^G\d{4}\.md$/.test(path))
		.sort()
	if (promptFiles.length > 1) {
		throw new Error('Only one experiment prompt may be uploaded per coordinator')
	}
	let registeredAgent:
		| {
				generation: string
				promptPath: string
				instructionsSha256: string
				agent: ReturnType<typeof amp.createAgent>
		  }
		| undefined
	if (promptFiles.length === 1) {
		const generation = promptFiles[0].slice(0, -3)
		const promptPath = join(inputDirectory, promptFiles[0])
		const instructions = readFileSync(promptPath)
		const agent = amp.createAgent({
			name: 'Grok 4.6',
			model: config.model,
			instructions: instructions.toString(),
			tools: config.tools,
			reasoningEffort: config.reasoning_effort,
			compactionThresholdTokens: config.compaction_threshold_tokens,
			display: { label: `experiment-${generation}` },
		})
		amp.registerAgentMode({
			key: 'grok46-experiment',
			label: 'grok46-experiment',
			description: `Runs the uploaded immutable ${generation} experiment prompt.`,
			agent: agent.definition,
		})
		registeredAgent = {
			generation,
			promptPath,
			instructionsSha256: sha256(instructions),
			agent,
		}
	}
	const highAgent = amp.createAgent({
		extends: 'high',
	})
	amp.registerAgentMode({
		key: 'grok46-reference-high',
		label: 'grok46-reference-high',
		description: 'Runs an unmodified inherited built-in high agent.',
		agent: highAgent.definition,
	})

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
					description: 'One of high, grok46-baseline, or grok46-candidate.',
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
			if (!['high', 'grok46-baseline', 'grok46-candidate'].includes(mode)) {
				throw new Error('invalid experiment mode')
			}
			if ((mode === 'grok46-candidate') === (generation === 'G0000')) {
				throw new Error('high/baseline require G0000 and candidates require a later generation')
			}
			if (!/^[SL]\d{2}$/.test(scenarioID)) throw new Error('invalid scenario ID')

			const promptPath = pathWithin(root, '.amp/experiment-inputs', instructionsPath)
			const instructions = readFileSync(promptPath)
			if (sha256(instructions) !== expectedInstructionsHash) {
				throw new Error('uploaded prompt digest mismatch')
			}
			if (
				mode !== 'high' &&
				(!registeredAgent ||
					registeredAgent.generation !== generation ||
					registeredAgent.promptPath !== promptPath ||
					registeredAgent.instructionsSha256 !== expectedInstructionsHash)
			) {
				throw new Error(
					'uploaded prompt is not the registered experiment agent; reload plugins after upload',
				)
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

			const agent = mode === 'high' ? highAgent : registeredAgent!.agent
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
				let finalAnswer: string | undefined
				try {
					const response = await child.waitForResponse({ timeoutMs: 30 * 60 * 1000 })
					finalAnswer = response.content
						.filter((block) => block.type === 'text')
						.map((block) => block.text)
						.join('')
				} catch (waitError) {
					const remote = amp.threads.get(child.id)
					const deadline = Date.now() + 30 * 60 * 1000
					while (Date.now() < deadline) {
						await delay(5_000)
						try {
							if ((await remote.state.get()) !== 'idle') continue
							const [finalMessage] = await remote.messages({
								full: true,
								from: 'end',
								limit: 1,
								roles: ['assistant'],
							})
							finalAnswer = finalMessage?.content
								.filter((block) => block.type === 'text')
								.map((block) => block.text)
								.join('')
							break
						} catch {
							// Orb agent errors can be transient; keep polling this same child.
						}
					}
					if (!finalAnswer) throw waitError
				}
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
