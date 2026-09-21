<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="splash"
      :class="{ leaving }"
      role="dialog"
      aria-label="开场动画"
      @click="skip"
    >
      <div class="stage" @click.stop>
        <div class="pot-wrap">
          <div class="steam s1" />
          <div class="steam s2" />
          <div class="steam s3" />
          <div class="pot">
            <div class="rim" />
            <div class="body">
              <img src="/assets/brand-bowl.png" alt="" class="bowl" />
              <div class="broth" />
              <div class="ladle" />
            </div>
            <div class="base" />
          </div>
          <div class="embers" />
        </div>
        <p class="title">海龟汤</p>
        <p class="sub">炉火正旺 · 汤将开席</p>
        <button class="skip" type="button" @click="skip">跳过</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

const emit = defineEmits(['done'])
const visible = ref(true)
const leaving = ref(false)
let autoTimer = 0
let leaveTimer = 0

const finish = () => {
  if (!visible.value) return
  leaving.value = true
  leaveTimer = window.setTimeout(() => {
    visible.value = false
    emit('done')
  }, 420)
}

const skip = () => finish()

onMounted(() => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  autoTimer = window.setTimeout(finish, reduce ? 400 : 2200)
})

onUnmounted(() => {
  window.clearTimeout(autoTimer)
  window.clearTimeout(leaveTimer)
})
</script>

<style scoped>
.splash {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  background:
    radial-gradient(ellipse at 50% 70%, rgba(212, 163, 92, 0.22), transparent 55%),
    linear-gradient(165deg, #061014 0%, #0c1f24 55%, #081216 100%);
  padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom)
    env(safe-area-inset-left);
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.splash.leaving {
  opacity: 0;
  transform: scale(1.03);
  pointer-events: none;
}

.stage {
  text-align: center;
  width: min(320px, 86vw);
}

.pot-wrap {
  position: relative;
  height: 210px;
  margin: 0 auto 1.1rem;
}

.pot {
  position: absolute;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  width: 150px;
}

.rim {
  height: 14px;
  border-radius: 999px;
  background: linear-gradient(90deg, #8a6a3d, #e8b86a, #8a6a3d);
  box-shadow: 0 2px 0 rgba(0, 0, 0, 0.35);
}

.body {
  position: relative;
  margin-top: -4px;
  height: 98px;
  border-radius: 0 0 48% 48% / 0 0 70% 70%;
  background: linear-gradient(180deg, #2a4a52 0%, #163038 70%, #0e2228 100%);
  border: 2px solid rgba(212, 163, 92, 0.35);
  overflow: hidden;
}

.bowl {
  position: absolute;
  inset: 8px 18px auto;
  width: calc(100% - 36px);
  height: 52px;
  object-fit: cover;
  border-radius: 50%;
  opacity: 0.9;
  mix-blend-mode: soft-light;
}

.broth {
  position: absolute;
  left: 12%;
  right: 12%;
  top: 28%;
  height: 42%;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 40%, #c9893a, #7a4a1e 70%);
  animation: simmer 1.4s ease-in-out infinite;
}

.ladle {
  position: absolute;
  width: 54px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, #d4a35c, #f0d09a);
  top: 36%;
  left: 28%;
  transform-origin: 85% 50%;
  animation: stir 1.6s ease-in-out infinite;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
}

.base {
  width: 70%;
  height: 10px;
  margin: 6px auto 0;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.35);
  filter: blur(2px);
}

.embers {
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 120px;
  height: 28px;
  transform: translateX(-50%);
  background: radial-gradient(ellipse, rgba(232, 120, 60, 0.55), transparent 70%);
  filter: blur(6px);
  animation: flicker 0.9s ease-in-out infinite alternate;
}

.steam {
  position: absolute;
  left: 50%;
  bottom: 130px;
  width: 18px;
  height: 56px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(232, 242, 240, 0.55), transparent);
  filter: blur(4px);
  opacity: 0;
  animation: rise 2s ease-in-out infinite;
}

.s1 {
  margin-left: -36px;
  animation-delay: 0s;
}
.s2 {
  margin-left: -8px;
  animation-delay: 0.35s;
}
.s3 {
  margin-left: 20px;
  animation-delay: 0.7s;
}

.title {
  font-family: var(--font-display);
  font-size: 2.4rem;
  letter-spacing: 0.18em;
  margin: 0 0 0.35rem;
  animation: fadeUp 0.7s ease both 0.15s;
}

.sub {
  margin: 0 0 1.25rem;
  color: var(--muted);
  letter-spacing: 0.12em;
  font-size: 0.9rem;
  animation: fadeUp 0.7s ease both 0.3s;
}

.skip {
  border: 1px solid var(--line);
  background: rgba(232, 242, 240, 0.06);
  color: var(--muted);
  border-radius: 999px;
  padding: 0.55rem 1.1rem;
  cursor: pointer;
  min-height: 44px;
}

@keyframes simmer {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.04);
  }
}

@keyframes stir {
  0%,
  100% {
    transform: rotate(-18deg);
  }
  50% {
    transform: rotate(22deg);
  }
}

@keyframes rise {
  0% {
    opacity: 0;
    transform: translateY(12px) scaleX(0.8);
  }
  35% {
    opacity: 0.85;
  }
  100% {
    opacity: 0;
    transform: translateY(-46px) scaleX(1.15);
  }
}

@keyframes flicker {
  from {
    opacity: 0.55;
    transform: translateX(-50%) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) scale(1.08);
  }
}

@media (prefers-reduced-motion: reduce) {
  .broth,
  .ladle,
  .steam,
  .embers {
    animation: none;
  }
  .steam {
    opacity: 0.35;
  }
}
</style>
