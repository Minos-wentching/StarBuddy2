<template>
  <div class="analytics-root">
    <ShaderBackground role="manager" :intensity="0.15" />

    <div class="scroll-container">
      <!-- 标题和导航 -->
      <div style="position: relative; text-align: center; margin-bottom: 28px;">
        <v-btn
          icon
          variant="text"
          size="small"
          style="position: absolute; left: 0; top: 50%; transform: translateY(-50%); color: rgba(255,255,255,0.6);"
          @click="$router.push('/')"
        >
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <div class="page-title">数据分析</div>
        <div class="body-text" style="margin-top: 4px; font-size: 13px;">成长过程的可视化分析</div>
      </div>

      <!-- 情绪分析卡片 -->
      <div class="glass-card" style="margin-bottom: 20px;">
        <div class="section-title" style="margin-bottom: 14px;">
          <v-icon size="20" color="deep-purple" class="mr-2">mdi-heart-pulse</v-icon>
          情绪分析
        </div>

        <div style="margin-bottom: 16px;">
          <div class="subsection-title">当前情绪状态</div>
          <div class="d-flex align-center" style="margin-bottom: 10px;">
            <v-progress-linear
              :model-value="personaStore.emotionIntensity * 100"
              :color="emotionBarColor"
              height="12"
              rounded
              class="mr-3"
              bg-color="rgba(255,255,255,0.08)"
            ></v-progress-linear>
            <div style="font-size: 22px; font-weight: 700; color: white; min-width: 48px; text-align: right;">
              {{ Math.round(personaStore.emotionIntensity * 100) }}%
            </div>
          </div>
          <div class="d-flex align-center" style="gap: 8px;">
            <v-chip size="small" :color="emotionBarColor" variant="flat">
              {{ personaStore.emotionLevel }}
            </v-chip>
            <span class="body-text">情绪强度</span>
          </div>
        </div>

        <div class="divider"></div>
        <div style="padding-top: 14px;">
          <div class="subsection-title">情绪趋势</div>
          <div v-if="emotionStats.length === 0" class="empty-hint">暂无足够的历史数据</div>
          <div v-else>
            <div v-for="stat in emotionStats" :key="stat.level" style="margin-bottom: 10px;">
              <div class="d-flex justify-space-between body-text" style="margin-bottom: 4px;">
                <span>{{ stat.level }}</span>
                <span>{{ stat.count }}次</span>
              </div>
              <v-progress-linear
                :model-value="(stat.count / totalEmotionRecords) * 100"
                :color="stat.color"
                height="8"
                rounded
                bg-color="rgba(255,255,255,0.08)"
              ></v-progress-linear>
            </div>
          </div>
        </div>
      </div>

      <!-- 人格分布分析 -->
      <div class="glass-card" style="margin-bottom: 20px;">
        <div class="section-title" style="margin-bottom: 14px;">
          <v-icon size="20" color="indigo" class="mr-2">mdi-account-group</v-icon>
          人格伙伴分布
        </div>
        <div class="d-flex align-center" style="margin-bottom: 16px;">
          <v-avatar size="52" class="mr-4" style="background: rgba(255,255,255,0.12);">
            <v-icon color="white" size="24">{{ personaIcon }}</v-icon>
          </v-avatar>
          <div>
            <div style="font-size: 20px; font-weight: 700; color: white;">{{ personaStore.personaDisplay }}</div>
            <div class="body-text" style="margin-top: 2px;">{{ personaStore.personaDescription }}</div>
          </div>
        </div>
        <div class="divider"></div>
        <div style="padding-top: 14px;">
          <div class="subsection-title">伙伴切换统计</div>
          <div v-if="personaStats.length === 0" class="empty-hint">暂无伙伴切换记录</div>
          <div v-else>
            <div v-for="stat in personaStats" :key="stat.persona" style="margin-bottom: 12px;">
              <div class="d-flex align-center">
                <v-avatar :size="24" style="background: rgba(255,255,255,0.12);" class="mr-2">
                  <v-icon size="14" color="white">{{ getPersonaIcon(stat.persona) }}</v-icon>
                </v-avatar>
                <div class="flex-grow-1">
                  <div class="d-flex justify-space-between body-text" style="margin-bottom: 4px;">
                    <span>{{ getPersonaDisplay(stat.persona) }}</span>
                    <span>{{ stat.count }}次 ({{ stat.percentage }}%)</span>
                  </div>
                  <v-progress-linear
                    :model-value="stat.percentage"
                    :color="getPersonaColor(stat.persona)"
                    height="6"
                    rounded
                    bg-color="rgba(255,255,255,0.08)"
                  ></v-progress-linear>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 议会分析 -->
      <div class="glass-card" style="margin-bottom: 20px;">
        <div class="section-title" style="margin-bottom: 14px;">
          <v-icon size="20" color="orange" class="mr-2">mdi-forum</v-icon>
          会议分析
        </div>
        <div class="d-flex align-center" style="margin-bottom: 16px;">
          <v-avatar size="52" class="mr-4" style="background: rgba(255,255,255,0.12);">
            <v-icon color="white" size="24">
              {{ personaStore.isInnerCouncilActive ? 'mdi-forum' : 'mdi-forum-outline' }}
            </v-icon>
          </v-avatar>
          <div>
            <div style="font-size: 20px; font-weight: 700; color: white;">
              {{ personaStore.isInnerCouncilActive ? '会议进行中' : '会议未进行' }}
            </div>
            <div v-if="personaStore.isInnerCouncilActive" class="body-text" style="margin-top: 2px;">
              第 {{ personaStore.councilProgress.currentRound }} 轮 / 共 {{ personaStore.councilProgress.totalRounds }} 轮
            </div>
            <div v-else class="body-text" style="margin-top: 2px;">
              会议将在情绪强度超过阈值时自动触发
            </div>
          </div>
        </div>
        <div class="divider"></div>
        <div style="padding-top: 14px;">
          <div class="subsection-title">会议历史</div>
          <div v-if="councilStats.rounds === 0" class="empty-hint">暂无会议记录</div>
          <div v-else class="d-flex" style="text-align: center;">
            <div class="flex-grow-1" style="padding: 8px;">
              <div style="font-size: 28px; font-weight: 700; color: white;">{{ councilStats.rounds }}</div>
              <div class="body-text" style="font-size: 12px;">总轮次</div>
            </div>
            <div style="width: 1px; background: rgba(255,255,255,0.1); margin: 4px 0;"></div>
            <div class="flex-grow-1" style="padding: 8px;">
              <div style="font-size: 28px; font-weight: 700; color: white;">{{ councilStats.completed }}</div>
              <div class="body-text" style="font-size: 12px;">完成会议</div>
            </div>
            <div style="width: 1px; background: rgba(255,255,255,0.1); margin: 4px 0;"></div>
            <div class="flex-grow-1" style="padding: 8px;">
              <div style="font-size: 28px; font-weight: 700; color: white;">{{ councilStats.averageRounds }}</div>
              <div class="body-text" style="font-size: 12px;">平均轮次</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 核心信念分析 -->
      <div class="glass-card">
        <div class="section-title" style="margin-bottom: 14px;">
          <v-icon size="20" color="teal" class="mr-2">mdi-brain</v-icon>
          核心行为模式分析
        </div>
        <div v-if="personaStore.coreBeliefs.length === 0" class="empty-hint" style="padding: 20px 0;">
          <v-icon size="40" style="color: rgba(255,255,255,0.3); margin-bottom: 12px;">mdi-brain-outline</v-icon>
          <p>暂无核心行为模式记录</p>
          <p style="font-size: 12px; margin-top: 4px;">行为模式会在会议结束后由星星向导提炼</p>
        </div>
        <div v-else>
          <div style="margin-bottom: 16px;">
            <div class="subsection-title">积极模式</div>
            <div v-if="positiveBeliefs.length === 0" class="empty-hint">暂无积极模式</div>
            <div v-else class="d-flex flex-wrap" style="gap: 8px;">
              <v-chip v-for="belief in positiveBeliefs" :key="belief.content" size="large" class="glass-chip">
                <v-icon start style="color: rgba(255,255,255,0.7);">mdi-emoticon-happy</v-icon>
                {{ belief.content }}
              </v-chip>
            </div>
          </div>
          <div class="divider"></div>
          <div style="padding-top: 14px;">
            <div class="subsection-title">消极模式</div>
            <div v-if="negativeBeliefs.length === 0" class="empty-hint">暂无消极模式</div>
            <div v-else class="d-flex flex-wrap" style="gap: 8px;">
              <v-chip v-for="belief in negativeBeliefs" :key="belief.content" size="large" class="glass-chip">
                <v-icon start style="color: rgba(255,255,255,0.7);">mdi-emoticon-sad</v-icon>
                {{ belief.content }}
              </v-chip>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePersonaStore } from '@/stores/persona'
import { getPersonaDisplay, getPersonaIcon, getPersonaColor, getEmotionColor } from '@/composables/usePersona'
import ShaderBackground from '@/components/ShaderBackground.vue'

const personaStore = usePersonaStore()

const emotionBarColor = computed(() => getEmotionColor(personaStore.emotionIntensity))

const emotionStats = computed(() => {
  const stats = [
    { level: '平静', threshold: 0.3, color: '#4caf50', count: 0 },
    { level: '中等', threshold: 0.7, color: '#ff9800', count: 0 },
    { level: '强烈', threshold: 1.0, color: '#f44336', count: 0 }
  ]
  personaStore.personaHistory.forEach(entry => {
    const intensity = entry.intensity || 0
    if (intensity < 0.3) stats[0].count++
    else if (intensity < 0.7) stats[1].count++
    else stats[2].count++
  })
  return stats.filter(stat => stat.count > 0)
})

const totalEmotionRecords = computed(() => emotionStats.value.reduce((sum, stat) => sum + stat.count, 0))

const personaIcon = computed(() => personaStore.personaIcon)

const personaStats = computed(() => {
  const stats = {}
  const personas = ['manager', 'exiles', 'firefighters', 'counselor']
  personas.forEach(p => { stats[p] = { persona: p, count: 0 } })
  personaStore.personaHistory.forEach(entry => {
    if (stats[entry.to]) stats[entry.to].count++
  })
  const total = personaStore.personaHistory.length || 1
  return Object.values(stats)
    .map(stat => ({ ...stat, percentage: Math.round((stat.count / total) * 100) }))
    .filter(stat => stat.count > 0)
    .sort((a, b) => b.count - a.count)
})

const councilStats = computed(() => {
  const rounds = personaStore.councilRounds.length
  const completed = personaStore.councilConclusion ? 1 : 0
  const averageRounds = rounds > 0 ? Math.round(rounds / (completed || 1)) : 0
  return { rounds, completed, averageRounds }
})

const positiveBeliefs = computed(() => personaStore.coreBeliefs.filter(b => b.valence === 'positive'))
const negativeBeliefs = computed(() => personaStore.coreBeliefs.filter(b => b.valence === 'negative'))
</script>

<style scoped>
.analytics-root {
  position: fixed;
  inset: 0;
  overflow: hidden;
}
.scroll-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 24px 20px 60px;
  height: 100vh;
  overflow-y: auto;
  position: relative;
  z-index: 10;
}
.page-title {
  font-size: 28px;
  font-weight: 700;
  color: white;
  letter-spacing: 2px;
}
.glass-card {
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 16px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255,255,255,0.85);
  display: flex;
  align-items: center;
}
.subsection-title {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255,255,255,0.75);
  margin-bottom: 10px;
}
.body-text {
  color: rgba(255,255,255,0.7);
  font-size: 14px;
}
.empty-hint {
  text-align: center;
  padding: 16px;
  color: rgba(255,255,255,0.4);
  font-size: 13px;
}
.divider {
  height: 1px;
  background: rgba(255,255,255,0.08);
}
.glass-chip {
  background: rgba(255,255,255,0.08) !important;
  color: rgba(255,255,255,0.7) !important;
  border: 1px solid rgba(255,255,255,0.1);
}
.scroll-container::-webkit-scrollbar { width: 0; background: transparent; }
.scroll-container { scrollbar-width: none; }
:deep(.v-progress-linear__background) { opacity: 1 !important; }
</style>
