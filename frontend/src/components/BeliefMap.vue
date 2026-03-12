<template>
  <div class="belief-map" ref="mapContainer">
    <div v-if="!beliefs.length" class="empty-state">
      <v-icon size="32" color="rgba(255,255,255,0.4)">mdi-star-four-points-outline</v-icon>
      <span class="empty-text">尚未发现核心信念</span>
    </div>
    <div v-else class="belief-constellation">
      <div
        v-for="(belief, i) in beliefs"
        :key="i"
        class="belief-node"
        :class="{ 'belief-new': belief._isNew }"
        :style="getNodeStyle(belief, i)"
        :title="belief.content"
      >
        <div class="belief-glow" :style="getGlowStyle(belief)"></div>
        <div class="belief-label">{{ truncate(belief.content, 12) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, ref } from 'vue'
import { usePersonaStore } from '@/stores/persona'

const personaStore = usePersonaStore()
const mapContainer = ref(null)

const beliefs = computed(() => {
  return (personaStore.coreBeliefs || []).slice(0, 8).map((b, i) => ({
    ...b,
    _isNew: b._isNew || false,
  }))
})

// Mark new beliefs for animation
let prevBeliefCount = 0
watch(() => personaStore.coreBeliefs.length, (newLen) => {
  if (newLen > prevBeliefCount) {
    // Mark last added beliefs as new
    for (let i = prevBeliefCount; i < newLen; i++) {
      if (personaStore.coreBeliefs[i]) {
        personaStore.coreBeliefs[i]._isNew = true
        setTimeout(() => {
          if (personaStore.coreBeliefs[i]) {
            personaStore.coreBeliefs[i]._isNew = false
          }
        }, 2000)
      }
    }
  }
  prevBeliefCount = newLen
})

const truncate = (text, len) => text && text.length > len ? text.slice(0, len) + '...' : text

// Position nodes in a circular/organic layout
const getNodeStyle = (belief, index) => {
  const total = beliefs.value.length
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2
  const radius = 35 // percentage
  const cx = 50 + radius * Math.cos(angle)
  const cy = 50 + radius * Math.sin(angle)
  const intensity = belief.intensity || 5
  const size = 28 + (intensity / 10) * 24 // 28-52px

  const isNegative = belief.valence === 'negative' || (typeof belief.valence === 'number' && belief.valence < 0)
  const color = isNegative ? 'rgba(100, 160, 255, 0.9)' : 'rgba(255, 180, 80, 0.9)'

  return {
    left: `${cx}%`,
    top: `${cy}%`,
    width: `${size}px`,
    height: `${size}px`,
    color,
    '--glow-color': isNegative ? 'rgba(100, 160, 255, 0.4)' : 'rgba(255, 180, 80, 0.4)',
    animationDelay: `${index * 0.3}s`,
  }
}

const getGlowStyle = (belief) => {
  const isNegative = belief.valence === 'negative' || (typeof belief.valence === 'number' && belief.valence < 0)
  return {
    background: isNegative
      ? 'radial-gradient(circle, rgba(100, 160, 255, 0.6) 0%, transparent 70%)'
      : 'radial-gradient(circle, rgba(255, 180, 80, 0.6) 0%, transparent 70%)',
  }
}
</script>

<style scoped>
.belief-map {
  position: relative;
  width: 100%;
  height: 200px;
  overflow: hidden;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 8px;
}

.empty-text {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
}

.belief-constellation {
  position: relative;
  width: 100%;
  height: 100%;
}

.belief-node {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: default;
  animation: node-float 4s ease-in-out infinite alternate;
  transition: transform 0.3s ease;
}

.belief-node:hover {
  transform: translate(-50%, -50%) scale(1.2);
  z-index: 10;
}

.belief-glow {
  position: absolute;
  width: 200%;
  height: 200%;
  border-radius: 50%;
  animation: glow-pulse 3s ease-in-out infinite alternate;
}

.belief-label {
  font-size: 10px;
  color: rgba(255,255,255,0.9);
  white-space: nowrap;
  text-shadow: 0 1px 4px rgba(0,0,0,0.5);
  position: relative;
  z-index: 1;
}

.belief-new {
  animation: node-birth 0.8s ease-out;
}

@keyframes node-float {
  0% { transform: translate(-50%, -50%) translateY(0); }
  100% { transform: translate(-50%, -50%) translateY(-6px); }
}

@keyframes glow-pulse {
  0% { opacity: 0.5; transform: scale(0.9); }
  100% { opacity: 1; transform: scale(1.1); }
}

@keyframes node-birth {
  0% { opacity: 0; transform: translate(-50%, -50%) scale(0); }
  50% { transform: translate(-50%, -50%) scale(1.3); }
  100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
}
</style>
