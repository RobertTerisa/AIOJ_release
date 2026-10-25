import { randomUUID } from 'node:crypto'

export const name = 'monitor'
export const inject = ['llm', 'agents']

const WINDOW_SIZE = 6
const NEEDLE = "```cpp"
const REGENERATE_MESSAGE = '你违反了AGENTS.md中关于禁止直接给出可编译代码的规定，请重新生成'
const REGENERATION_LIMIT = 3

const regenerations = new Map()

/** 为一个文本流维护长度为 6 的滑动窗口；命中就抛异常。 */
function createSlidingWindow() {
  let window = ''
  return {
    push(text) {
      if (typeof text !== 'string' || text.length === 0) return
      for (const char of text) {
        window = (window + char).slice(-WINDOW_SIZE)
        if (window.includes(NEEDLE)) {
          throw new Error(`[monitor] detected forbidden sequence: ${NEEDLE}`)
        }
      }
    },
  }
}

/** 构造发给 Agent 的违规提醒消息。 */
function createRegenerateMessage() {
  return {
    id: randomUUID(),
    role: 'user',
    content: [{ type: 'text', text: REGENERATE_MESSAGE }],
    source: { kind: 'plugin:monitor' },
  }
}

/**
 * 取消当前生成，并让 Agent 用提醒消息开启下一轮。
 *
 * 顺序必须是 cancel -> followup：
 * followup 会看到 signal 已 aborted，把消息锁存到 next-turn 并唤醒 driver。
 */
function stopAndRegenerate(ctx, options) {
  const sessionId = options?.sessionId
  const agent = sessionId === undefined ? undefined : ctx.agents.get(sessionId)

  if (agent === undefined) {
    throw new Error('[monitor] cannot locate the running agent for this request')
  }

  const count = (regenerations.get(sessionId) ?? 0) + 1
  if (count > REGENERATION_LIMIT) {
    regenerations.delete(sessionId)
    throw new Error('[monitor] model repeatedly violated the no-code rule')
  }
  regenerations.set(sessionId, count)

  agent.cancel({ kind: 'user' })
  agent.followup(createRegenerateMessage())
}

/** 一次正常结束的 attempt 会清掉该 session 的连续违规计数。 */
function clearRegenerations(options) {
  const sessionId = options?.sessionId
  if (sessionId !== undefined) regenerations.delete(sessionId)
}

/**
 * 包装 LLM 输出流。
 * 只检查模型对外输出的正文（text-delta）；推理内容（reasoning-delta）不参与拦截。
 * 命中违规序列时：先触发 onViolation，再抛出异常停止当前流。
 */
function wrapChunkStream(stream, onViolation, onAttemptFinished) {
  return (async function* () {
    const window = createSlidingWindow()
    let stopped = false

    for await (const chunk of stream) {
      if (!stopped && chunk !== null && typeof chunk === 'object') {
        if (chunk.type === 'text-delta' && typeof chunk.text === 'string') {
          try {
            window.push(chunk.text)
          } catch (error) {
            stopped = true
            onViolation()
            throw error
          }
        }

        if (chunk.type === 'finish') {
          onAttemptFinished()
        }
      }

      if (!stopped) yield chunk
    }
  })()
}

export function monitor(ctx) {
  ctx.on('llm/stream', (options, next) => {
    if (options === null || typeof options !== 'object' || options.purpose !== undefined) {
      return next()
    }

    return wrapChunkStream(
      next(),
      () => stopAndRegenerate(ctx, options),
      () => clearRegenerations(options),
    )
  })
}

export { monitor as apply }
