<template>
  <div class="shader-bg-root">
    <canvas ref="canvas"></canvas>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'

const props = defineProps({
  role: { type: String, default: 'manager' },
  intensity: { type: Number, default: 0.2 }, // 0~1
})

const canvas = ref(null)
let renderer, scene, camera, mesh, uniforms, rafId
let targetA = null
let targetB = null
let lastFrameTime = 0
let resizeTimer = null

const isMobile = window.matchMedia('(hover: none)').matches || window.matchMedia('(prefers-reduced-motion: reduce)').matches

// 粉紫基调调色板（统一底色，保持轻微角色区分）
const rolePalettes = {
  manager: { a: new THREE.Color('#c5ddf5'), b: new THREE.Color('#5B9BD5') },
  exiles: { a: new THREE.Color('#fde0c8'), b: new THREE.Color('#F4B183') },
  firefighters: { a: new THREE.Color('#d4ecc6'), b: new THREE.Color('#A9D18E') },
  counselor: { a: new THREE.Color('#ddd6ef'), b: new THREE.Color('#B4A7D6') },
}

const FBM_ITERATIONS = isMobile ? 3 : 5
const PARTICLE_COUNT = isMobile ? 8 : 20

const frag = /* glsl */ `
precision highp float;
uniform vec2 uResolution;
uniform float uTime;
uniform float uIntensity;
uniform vec3 uColorA;
uniform vec3 uColorB;

float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453123); }
float noise(in vec2 p){
  vec2 i = floor(p);
  vec2 f = fract(p);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  vec2 u = f*f*(3.0-2.0*f);
  return mix(a, b, u.x) + (c - a)*u.y*(1.0 - u.x) + (d - b)*u.x*u.y;
}

float fbm(vec2 p){
  float v = 0.0;
  float a = 0.5;
  for(int i=0;i<${FBM_ITERATIONS};i++){
    v += a * noise(p);
    p *= 2.0;
    a *= 0.5;
  }
  return v;
}

// Particle layer - floating dots based on intensity
float particles(vec2 uv, float time, float intensity) {
  float result = 0.0;
  float count = mix(3.0, ${PARTICLE_COUNT}.0, intensity);
  for(float i = 0.0; i < ${PARTICLE_COUNT}.0; i++) {
    if(i >= count) break;
    vec2 seed = vec2(i * 17.32, i * 31.78);
    float speed = mix(0.02, 0.15, intensity) * (0.5 + hash(seed) * 0.5);
    vec2 pos = vec2(
      fract(hash(seed) + time * speed * 0.3),
      fract(hash(seed + 100.0) + time * speed * 0.5)
    );
    float dist = length(uv - pos);
    float size = mix(0.002, 0.006, hash(seed + 200.0)) * (0.7 + intensity * 0.5);
    float glow = smoothstep(size * 3.0, size * 0.5, dist);
    float alpha = 0.15 + intensity * 0.35;
    result += glow * alpha;
  }
  return result;
}

void main(){
  vec2 uv = gl_FragCoord.xy / uResolution.xy;
  vec2 p = (uv - 0.5) * vec2(uResolution.x / uResolution.y, 1.0);

  float speed = mix(0.03, 0.35, clamp(uIntensity, 0.0, 1.0));
  float freq  = mix(0.8, 2.5, clamp(uIntensity, 0.0, 1.0));

  float t = uTime * speed;
  float n = fbm(p * freq + t);

  vec3 col = mix(uColorA, uColorB, smoothstep(0.2, 0.8, n));

  // Breathing effect
  float breathe = 0.04 * sin(uTime * 0.5);
  col += breathe;

  // Particle overlay
  float ptcl = particles(uv, uTime, clamp(uIntensity, 0.0, 1.0));
  col += vec3(ptcl) * mix(vec3(1.0), (uColorA + uColorB) * 0.5 + 0.5, 0.5);

  // Subtle vignette
  float vig = 1.0 - 0.3 * length(uv - 0.5);
  col *= vig;

  gl_FragColor = vec4(col, 1.0);
}
`

function resize() {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    if (!canvas.value || !renderer) return
    const { clientWidth: w, clientHeight: h } = canvas.value
    renderer.setSize(w, h, false)
    uniforms.uResolution.value.set(w, h)
  }, 150)
}

function animate(now) {
  if (!lastFrameTime) lastFrameTime = now
  const delta = (now - lastFrameTime) / 1000
  lastFrameTime = now

  uniforms.uTime.value += delta
  if (targetA && targetB) {
    uniforms.uColorA.value.lerp(targetA, 0.05)
    uniforms.uColorB.value.lerp(targetB, 0.05)
  }
  renderer.render(scene, camera)
  rafId = requestAnimationFrame(animate)
}

function setPaletteByRole(role) {
  const p = rolePalettes[role] || rolePalettes.manager
  targetA = p.a.clone()
  targetB = p.b.clone()
}

function handleVisibilityChange() {
  if (document.hidden) {
    cancelAnimationFrame(rafId)
    rafId = null
  } else {
    lastFrameTime = 0
    rafId = requestAnimationFrame(animate)
  }
}

onMounted(() => {
  const el = canvas.value
  renderer = new THREE.WebGLRenderer({
    canvas: el,
    antialias: false,
    alpha: true,
    powerPreference: 'default'
  })
  renderer.setPixelRatio(isMobile ? 1 : Math.min(window.devicePixelRatio, 2))

  scene = new THREE.Scene()
  camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)

  uniforms = {
    uTime: { value: 0 },
    uResolution: { value: new THREE.Vector2(1, 1) },
    uIntensity: { value: props.intensity },
    uColorA: { value: rolePalettes[props.role]?.a.clone() || rolePalettes.manager.a.clone() },
    uColorB: { value: rolePalettes[props.role]?.b.clone() || rolePalettes.manager.b.clone() },
  }

  const material = new THREE.ShaderMaterial({
    fragmentShader: frag,
    uniforms,
  })
  const quad = new THREE.PlaneGeometry(2, 2)
  mesh = new THREE.Mesh(quad, material)
  scene.add(mesh)

  resize()
  window.addEventListener('resize', resize)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  lastFrameTime = 0
  rafId = requestAnimationFrame(animate)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  window.removeEventListener('resize', resize)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  if (resizeTimer) clearTimeout(resizeTimer)
  if (mesh) {
    mesh.geometry.dispose()
    mesh.material.dispose()
  }
  if (renderer) renderer.dispose()
})

watch(() => props.intensity, (val) => {
  uniforms && (uniforms.uIntensity.value = val)
})

watch(() => props.role, (r) => {
  if (uniforms) setPaletteByRole(r)
}, { immediate: true })
</script>

<style scoped>
.shader-bg-root {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
canvas {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
