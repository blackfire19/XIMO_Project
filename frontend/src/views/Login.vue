<template>
  <div class="login-wrapper">
    <a-card class="login-card" title="XIMOSteel 登录">
      <a-form :model="form" @finish="onFinish" layout="vertical">
        <a-form-item label="用户名" name="username" :rules="[{ required: true }]">
          <a-input v-model:value="form.username" size="large" />
        </a-form-item>
        <a-form-item label="密码" name="password" :rules="[{ required: true }]">
          <a-input-password v-model:value="form.password" size="large" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" size="large" block :loading="loading">
            登录
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function onFinish() {
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push('/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}
.login-card {
  width: 360px;
}
</style>
