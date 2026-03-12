<template>
  <div class="council-debate-log">
    <!-- No data -->
    <div v-if="!rounds.length && !conclusion" class="empty-state">
      <v-icon size="48" color="rgba(255,255,255,0.3)">mdi-account-group</v-icon>
      <p class="empty-title">暂无会议记录</p>
      <p class="empty-hint">当情绪强度超过阈值时，感知精灵与规则守卫将展开对话</p>
    </div>

    <!-- Council in progress -->
    <div v-if="personaStore.isInnerCouncilActive" class="council-active-banner">
      <div class="pulse-dot"></div>
      <span>星球会议进行中 · 第 {{ personaStore.councilProgress.currentRound }} 轮</span>
    </div>

    <!-- Debate rounds - opposing layout -->
    <div v-if="rounds.length" class="debate-arena">
      <!-- Tug-of-war bar -->
      <div class="tug-bar">
        <div class="tug-label tug-exiles">感知精灵</div>
        <div class="tug-track">
          <div class="tug-fill" :style="tugStyle"></div>
          <div class="tug-center"></div>
        </div>
        <div class="tug-label tug-firefighters">规则守卫</div>
      </div>

      <!-- Rounds -->
      <div v-for="(round, idx) in rounds" :key="round.round" class="debate-round"
           :style="{ animationDelay: `${idx * 0.15}s` }">
        <div class="round-label">Round {{ round.round }}</div>

        <div class="debate-columns">
          <!-- Exiles (left, warm) -->
          <div class="debate-col col-exiles">
            <div class="debate-speaker">
              <v-icon size="16" color="#F4B183">mdi-creation</v-icon>
              <span class="speaker-name" style="color:#F4B183">感知精灵</span>
            </div>
            <div class="debate-text exiles-text">{{ round.exiles_argument }}</div>
          </div>

          <!-- VS divider -->
          <div class="vs-divider">
            <div class="vs-line"></div>
            <span class="vs-text">VS</span>
            <div class="vs-line"></div>
          </div>

          <!-- Firefighters (right, cool) -->
          <div class="debate-col col-firefighters">
            <div class="debate-speaker">
              <v-icon size="16" color="#A9D18E">mdi-shield-star</v-icon>
              <span class="speaker-name" style="color:#A9D18E">规则守卫</span>
            </div>
            <div class="debate-text firefighters-text">{{ round.firefighters_argument }}</div>
          </div>
        </div>

        <!-- Counselor analysis -->
        <div v-if="round.counselor_analysis" class="counselor-insight">
          <v-icon size="14" color="#B4A7D6" class="mr-1">mdi-star-shooting</v-icon>
          <span class="insight-label">星星向导对你说:</span>
          <span class="insight-text">{{ round.counselor_analysis }}</span>
        </div>
      </div>
    </div>

    <!-- Conclusion -->
    <div v-if="conclusion" class="conclusion-card">
      <div class="conclusion-header">
        <v-icon color="white" size="20" class="mr-2">mdi-lightbulb-on</v-icon>
        <span>会议结论</span>
      </div>
      <div class="conclusion-text">{{ conclusion }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePersonaStore } from '@/stores/persona'

const personaStore = usePersonaStore()

const rounds = computed(() => personaStore.councilRounds)
const conclusion = computed(() => personaStore.councilConclusion)

// Tug-of-war position: analyze which side has stronger arguments
const tugStyle = computed(() => {
  if (!rounds.value.length) return { width: '50%' }
  // Simple heuristic: longer argument = more forceful
  let idStrength = 0
  let superStrength = 0
  rounds.value.forEach(r => {
    idStrength += (r.exiles_argument || '').length
    superStrength += (r.firefighters_argument || '').length
  })
  const total = idStrength + superStrength || 1
  const idPercent = Math.max(20, Math.min(80, (idStrength / total) * 100))
  return { width: `${idPercent}%` }
})
</script>

<style scoped>
.council-debate-log {
  padding: 20px;
  color: white;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  gap: 8px;
}
.empty-title {
  color: rgba(255, 255, 255, 0.5);
  font-size: 15px;
}
.empty-hint {
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
}

/* Active banner */
.council-active-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  margin-bottom: 20px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
}
.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4fc3f7;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(79, 195, 247, 0.5); }
  50% { opacity: 0.7; box-shadow: 0 0 0 8px rgba(79, 195, 247, 0); }
}

/* Tug-of-war bar */
.tug-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 24px;
}
.tug-label {
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}
.tug-exiles { color: #F4B183; }
.tug-firefighters { color: #A9D18E; }
.tug-track {
  flex: 1;
  height: 6px;
  background: rgba(66, 165, 245, 0.3);
  border-radius: 3px;
  position: relative;
  overflow: hidden;
}
.tug-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(244, 177, 131, 0.7), rgba(244, 177, 131, 0.4));
  border-radius: 3px;
  transition: width 0.8s ease;
}
.tug-center {
  position: absolute;
  top: -3px;
  left: 50%;
  transform: translateX(-50%);
  width: 2px;
  height: 12px;
  background: rgba(255, 255, 255, 0.3);
}

/* Debate rounds */
.debate-round {
  margin-bottom: 20px;
  animation: round-in 0.4s ease-out both;
}
@keyframes round-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.round-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: 10px;
  text-align: center;
}

.debate-columns {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.debate-col {
  flex: 1;
  min-width: 0;
}

.debate-speaker {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.speaker-name {
  font-size: 12px;
  font-weight: 600;
}

.debate-text {
  font-size: 13px;
  line-height: 1.6;
  padding: 10px 14px;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.9);
}

.exiles-text {
  background: rgba(244, 177, 131, 0.1);
  border: 1px solid rgba(244, 177, 131, 0.2);
}

.firefighters-text {
  background: rgba(169, 209, 142, 0.1);
  border: 1px solid rgba(169, 209, 142, 0.2);
}

.vs-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding-top: 28px;
  flex-shrink: 0;
  width: 30px;
}
.vs-line {
  width: 1px;
  height: 16px;
  background: rgba(255, 255, 255, 0.15);
}
.vs-text {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
  font-weight: 700;
}

/* Counselor insight */
.counselor-insight {
  margin-top: 10px;
  padding: 8px 12px;
  background: rgba(180, 167, 214, 0.1);
  border: 1px solid rgba(180, 167, 214, 0.2);
  border-radius: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: flex-start;
  gap: 4px;
}
.insight-label {
  color: rgba(180, 167, 214, 0.8);
  font-weight: 600;
  flex-shrink: 0;
}

/* Conclusion */
.conclusion-card {
  margin-top: 24px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 12px;
  animation: conclusion-glow 2s ease-in-out infinite alternate;
}
@keyframes conclusion-glow {
  from { box-shadow: 0 0 10px rgba(255, 255, 255, 0.05); }
  to { box-shadow: 0 0 20px rgba(255, 255, 255, 0.1); }
}

.conclusion-header {
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: 700;
  color: white;
  margin-bottom: 10px;
}
.conclusion-text {
  font-size: 13px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.85);
}
</style>
