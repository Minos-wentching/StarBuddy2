// Legacy timeline player retained for reference.
// Current showcase flow uses manual memory-orb triggers instead of autoplay.
export function createScriptPlayer({ scenes = [], onScene, onFinish, onTick }) {
  const timeline = Array.isArray(scenes)
    ? [...scenes].sort((a, b) => Number(a.atMs || 0) - Number(b.atMs || 0))
    : []

  let timers = []
  let cursor = 0
  let elapsedMs = 0
  let running = false
  let startedAt = 0

  const clearTimers = () => {
    for (const timer of timers) clearTimeout(timer)
    timers = []
  }

  const emitTick = () => {
    if (typeof onTick === 'function') {
      onTick(elapsedMs, cursor)
    }
  }

  const scheduleFromCurrent = () => {
    clearTimers()

    if (cursor >= timeline.length) {
      running = false
      emitTick()
      if (typeof onFinish === 'function') onFinish()
      return
    }

    startedAt = Date.now() - elapsedMs
    running = true

    for (let i = cursor; i < timeline.length; i += 1) {
      const scene = timeline[i]
      const sceneAt = Number(scene.atMs || 0)
      const delay = Math.max(0, sceneAt - elapsedMs)
      const timer = setTimeout(() => {
        elapsedMs = sceneAt
        cursor = i + 1
        if (typeof onScene === 'function') onScene(scene, i)
        emitTick()

        if (cursor >= timeline.length) {
          clearTimers()
          running = false
          if (typeof onFinish === 'function') onFinish()
        }
      }, delay)
      timers.push(timer)
    }
  }

  return {
    start() {
      cursor = 0
      elapsedMs = 0
      scheduleFromCurrent()
      emitTick()
    },

    pause() {
      if (!running) return
      elapsedMs = Math.max(0, Date.now() - startedAt)
      clearTimers()
      running = false
      emitTick()
    },

    resume() {
      if (running) return
      scheduleFromCurrent()
      emitTick()
    },

    next() {
      if (cursor >= timeline.length) {
        if (typeof onFinish === 'function') onFinish()
        return
      }
      clearTimers()
      const index = cursor
      const scene = timeline[index]
      elapsedMs = Number(scene.atMs || elapsedMs)
      cursor = index + 1
      if (typeof onScene === 'function') onScene(scene, index)
      emitTick()
      scheduleFromCurrent()
    },

    stop() {
      clearTimers()
      running = false
      cursor = 0
      elapsedMs = 0
      emitTick()
    },

    getState() {
      return {
        cursor,
        elapsedMs: running ? Math.max(elapsedMs, Date.now() - startedAt) : elapsedMs,
        running,
      }
    },
  }
}
