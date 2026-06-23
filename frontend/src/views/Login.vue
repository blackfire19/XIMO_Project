<template>
  <div class="login-stage">
    <div class="login-card">
    <!-- 左：品牌 + 数据 -->
    <aside class="brand-panel">
      <div class="brand-glow"></div>

      <header class="brand-top">
        <span class="emblem">
          <img
            v-if="showLogo"
            :src="logoSrc"
            alt="西莫金属"
            class="emblem-img"
            @error="showLogo = false"
          />
          <span v-else class="emblem-fallback">XiMO</span>
        </span>
        <span class="wordmark">XIMOSTEEL</span>
      </header>

      <div class="brand-mid">
        <p class="brand-eyebrow">全球钢铁贸易管理平台</p>
        <h1 class="brand-title">西莫金属<br />外贸业务中枢</h1>
        <p class="brand-desc">询价、报价、订单、出运 —— 一体化协同，<br />让每一笔跨境钢铁贸易尽在掌握。</p>
      </div>

      <div class="brand-stats">
        <div class="stat">
          <div class="stat-num">38<span class="stat-unit">国</span></div>
          <div class="stat-label">出口覆盖</div>
        </div>
        <div class="stat">
          <div class="stat-num">12<span class="stat-unit">万吨</span></div>
          <div class="stat-label">年发运量</div>
        </div>
        <div class="stat">
          <div class="stat-num">99.2<span class="stat-unit">%</span></div>
          <div class="stat-label">准时交付</div>
        </div>
      </div>
    </aside>

    <!-- 右：登录表单 -->
    <main class="form-panel">
      <div class="form-box">
        <!-- 窄屏品牌头 -->
        <div class="mobile-brand">
          <span class="emblem emblem--sm">
            <img
              v-if="showLogo"
              :src="logoSrc"
              alt="西莫金属"
              class="emblem-img"
              @error="showLogo = false"
            />
            <span v-else class="emblem-fallback">XiMO</span>
          </span>
          <span class="mobile-brand-name">西莫金属</span>
        </div>

        <h2 class="form-title">欢迎登录</h2>
        <p class="form-sub">账户登录</p>

        <form class="login-form" @submit.prevent="onSubmit">
          <label class="field">
            <span class="field-label">用户名<em class="en">USERNAME</em></span>
            <input
              v-model.trim="form.username"
              class="field-input"
              type="text"
              autocomplete="username"
              placeholder="请输入用户名"
            />
          </label>

          <label class="field">
            <span class="field-label">密码<em class="en">PASSWORD</em></span>
            <input
              v-model="form.password"
              class="field-input"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
            />
          </label>

          <button class="submit-btn" type="submit" :disabled="loading">
            <span v-if="!loading">登 录</span>
            <span v-else>登录中…</span>
          </button>
        </form>

        <footer class="form-foot">© 2026 西摩钢铁集团 · XIMOSTEEL GROUP</footer>
      </div>
    </main>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const showLogo = ref(true)
const logoSrc = '/logo.jpg'
const form = reactive({ username: '', password: '' })

async function onSubmit() {
  if (!form.username || !form.password) {
    message.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push('/')
  } catch (err) {
    const msg = err?.response?.data?.detail || '用户名或密码错误'
    message.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@600;700&display=swap');

.login-stage {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  overflow: auto;
  font-family: 'Noto Sans SC', -apple-system, 'Microsoft YaHei', sans-serif;
  /* 外层金色拉丝背景：拉丝纹理 + 右上暖光 + 左下/底部暗角收边 + 主体金渐变 */
  background:
    repeating-linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.045) 0 1px,
      transparent 1px 22px
    ),
    radial-gradient(150% 110% at 50% 130%, rgba(44, 28, 8, 0.55), transparent 56%),
    radial-gradient(90% 90% at 8% 102%, rgba(44, 28, 8, 0.4), transparent 50%),
    radial-gradient(135% 125% at 74% 18%, rgba(255, 247, 220, 0.6), transparent 56%),
    linear-gradient(150deg, #d0a35d 0%, #ead08f 26%, #dab86f 54%, #c2994e 100%);
}

/* 悬浮登录卡片 */
.login-card {
  position: relative;
  display: flex;
  width: 100%;
  max-width: 1160px;
  height: min(90vh, 720px);
  border-radius: 28px;
  overflow: hidden;
  background: #faf8f3;
  box-shadow: 0 40px 90px -22px rgba(40, 28, 8, 0.55);
}

/* ===== 左：品牌面板 ===== */
.brand-panel {
  position: relative;
  z-index: 1;
  flex: 0 0 55%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 48px 52px 44px;
  color: #f2ede2;
  /* 顶层：45° 极淡斜向细密纹路（拉丝钢板质感）；下层：暖金光晕 + 近黑底 */
  background:
    repeating-linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.0185) 0 1px,
      transparent 1px 20px
    ),
    radial-gradient(95% 65% at 58% 2%, rgba(150, 112, 52, 0.42), transparent 60%),
    linear-gradient(160deg, #0b0a07 0%, #14110a 52%, #0d0b07 100%);
  overflow: hidden;
}
.brand-glow {
  position: absolute;
  width: 520px;
  height: 520px;
  border-radius: 50%;
  top: -160px;
  right: -160px;
  background: radial-gradient(circle, rgba(210, 173, 99, 0.2), transparent 70%);
  pointer-events: none;
}

.brand-top {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
}
.wordmark {
  font-family: 'IBM Plex Mono', Consolas, monospace;
  font-size: 15px;
  letter-spacing: 3px;
  color: #d3ad63;
}

.emblem {
  width: 52px;
  height: 52px;
  flex: 0 0 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(155deg, #241d12, #16130d);
  border: 1px solid rgba(211, 173, 99, 0.45);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}
.emblem-img {
  width: 86%;
  height: 86%;
  object-fit: contain;
}
.emblem-fallback {
  font-family: 'Noto Serif SC', serif;
  font-weight: 700;
  font-size: 15px;
  color: #2f4a8a;
}

.brand-mid {
  position: relative;
}
.brand-eyebrow {
  margin: 0 0 18px;
  font-family: 'IBM Plex Mono', Consolas, monospace;
  font-size: 12.5px;
  letter-spacing: 2px;
  color: #a89c84;
}
.brand-title {
  margin: 0;
  font-family: 'Noto Serif SC', 'Songti SC', STSong, serif;
  font-weight: 700;
  font-size: 42px;
  line-height: 1.28;
  letter-spacing: 3px;
  color: #f2ede2;
}
.brand-desc {
  margin: 26px 0 0;
  font-size: 14.5px;
  line-height: 2;
  letter-spacing: 1px;
  color: #9a8f79;
}

.brand-stats {
  position: relative;
  display: flex;
  gap: 44px;
}
.stat-num {
  font-family: 'Noto Serif SC', serif;
  font-weight: 700;
  font-size: 34px;
  color: #d6b16b;
  line-height: 1;
}
.stat-unit {
  font-size: 14px;
  margin-left: 3px;
  color: #e2ca90;
}
.stat-label {
  margin-top: 8px;
  font-size: 12.5px;
  letter-spacing: 1.5px;
  color: #9a8f79;
}

/* ===== 右：表单面板 ===== */
.form-panel {
  flex: 1 1 45%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 48px;
  background: linear-gradient(180deg, #faf8f3 0%, #f1ece1 100%);
  overflow-y: auto;
}
.form-box {
  width: 100%;
  max-width: 360px;
}
.mobile-brand {
  display: none;
}

.form-title {
  margin: 0;
  font-family: 'Noto Sans SC', -apple-system, sans-serif;
  font-weight: 700;
  font-size: 26px;
  letter-spacing: 1px;
  color: #2b2620;
}
.form-sub {
  margin: 6px 0 28px;
  font-size: 13px;
  letter-spacing: 2px;
  color: #9a9082;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.field-label {
  font-size: 13.5px;
  color: #4a443a;
}
.field-label .en {
  margin-left: 7px;
  font-style: normal;
  font-size: 11px;
  letter-spacing: 0.5px;
  color: #b3a99a;
}
.field-input {
  width: 100%;
  height: 46px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1px solid #e0d8c9;
  background: #ffffff;
  color: #2b2620;
  font-size: 15px;
  outline: none;
  box-shadow: inset 0 1px 2px rgba(43, 38, 32, 0.05);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.field-input::placeholder {
  color: #b8af9f;
}
.field-input:focus {
  border-color: #c9a253;
  box-shadow: 0 0 0 3px rgba(201, 162, 83, 0.15);
}

.submit-btn {
  margin-top: 10px;
  height: 46px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 15.5px;
  font-weight: 500;
  letter-spacing: 6px;
  color: #2a2208;
  background: linear-gradient(180deg, #dcbb70, #c9a253);
  box-shadow: 0 8px 20px rgba(201, 162, 83, 0.3);
  transition: transform 0.12s, box-shadow 0.2s, opacity 0.2s;
}
.submit-btn:hover:not(:disabled) {
  box-shadow: 0 10px 26px rgba(201, 162, 83, 0.42);
  transform: translateY(-1px);
}
.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}
.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.form-foot {
  margin-top: 32px;
  text-align: center;
  font-size: 11.5px;
  letter-spacing: 0.5px;
  color: #a89f90;
}

/* ===== 自适应 ===== */
@media (max-width: 880px) {
  .login-card {
    max-width: 440px;
    height: auto;
  }
  .brand-panel {
    display: none;
  }
  .form-panel {
    flex: 1 1 100%;
  }
  .mobile-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 30px;
  }
  .emblem--sm {
    width: 44px;
    height: 44px;
    flex-basis: 44px;
    border-color: rgba(200, 169, 106, 0.55);
  }
  .mobile-brand-name {
    font-family: 'Noto Serif SC', serif;
    font-weight: 700;
    font-size: 22px;
    letter-spacing: 4px;
    color: #2b2620;
  }
}

@media (max-width: 420px) {
  .login-stage {
    padding: 16px;
  }
  .form-panel {
    padding: 32px 24px;
  }
  .form-title {
    font-size: 26px;
  }
}
</style>
