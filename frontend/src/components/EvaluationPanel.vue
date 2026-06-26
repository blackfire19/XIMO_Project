<template>
  <div class="eval-panel">
    <a-divider orientation="left" style="font-size: 13px">评价记录</a-divider>

    <!-- 添加评价表单（仅老板/超管可见） -->
    <div v-if="canEvaluate" class="eval-form">
      <a-form layout="inline" @finish="submit" :model="form">
        <a-form-item label="评分" required>
          <a-input-number
            v-model:value="form.score"
            :min="1"
            :max="10"
            :precision="0"
            style="width: 80px"
            placeholder="1-10"
          />
          <span style="margin-left: 6px; color: #999; font-size: 12px">/ 10 分</span>
        </a-form-item>
        <a-form-item label="评语" style="flex: 1">
          <a-input
            v-model:value="form.comment"
            placeholder="选填评语..."
            allow-clear
            style="min-width: 200px"
          />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="submitting" size="small">
            提交评价
          </a-button>
        </a-form-item>
      </a-form>
    </div>

    <!-- 评价列表 -->
    <a-spin :spinning="loading">
      <a-empty v-if="!evaluations.length" :image="emptyImage" description="暂无评价" />
      <div v-else class="eval-list">
        <div v-for="ev in evaluations" :key="ev.id" class="eval-item">
          <div class="eval-header">
            <span class="eval-score">
              <span class="score-num">{{ ev.score }}</span>
              <span class="score-total"> / 10</span>
            </span>
            <span class="eval-meta">{{ ev.evaluator_name }} · {{ ev.created_at }}</span>
            <a-popconfirm
              v-if="canEvaluate"
              title="确认删除这条评价？"
              @confirm="remove(ev.id)"
            >
              <a-button type="link" danger size="small" style="padding: 0; margin-left: 8px">删除</a-button>
            </a-popconfirm>
          </div>
          <div v-if="ev.comment" class="eval-comment">{{ ev.comment }}</div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message, Empty } from 'ant-design-vue'
import { evaluationsApi } from '@/api/evaluations'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  targetType: { type: String, required: true },  // followup / inquiry / formal_order
  targetId: { type: Number, required: true },
  subjectId: { type: Number, required: true },   // 被评价员工 id
})

const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE
const auth = useAuthStore()
const canEvaluate = auth.hasRole('boss', 'super_admin')

const evaluations = ref([])
const loading = ref(false)
const submitting = ref(false)
const form = ref({ score: null, comment: '' })

async function load() {
  loading.value = true
  try {
    const res = await evaluationsApi.list({ target_type: props.targetType, target_id: props.targetId })
    evaluations.value = res.data
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.value.score) {
    message.warning('请填写评分')
    return
  }
  submitting.value = true
  try {
    await evaluationsApi.create({
      target_type: props.targetType,
      target_id: props.targetId,
      subject_id: props.subjectId,
      score: form.value.score,
      comment: form.value.comment || null,
    })
    message.success('评价已提交')
    form.value = { score: null, comment: '' }
    await load()
  } catch {
    message.error('提交失败')
  } finally {
    submitting.value = false
  }
}

async function remove(id) {
  try {
    await evaluationsApi.remove(id)
    message.success('已删除')
    await load()
  } catch {
    message.error('删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.eval-panel {
  margin-top: 8px;
}
/* 评价较多时内部滚动，避免撑高整列 */
.eval-list {
  max-height: 360px;
  overflow-y: auto;
  padding-right: 4px;
}
.eval-form {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 12px;
}
.eval-item {
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}
.eval-item:last-child {
  border-bottom: none;
}
.eval-header {
  display: flex;
  align-items: center;
  gap: 4px;
}
.eval-score {
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 4px;
  padding: 0 8px;
  margin-right: 8px;
}
.score-num {
  font-size: 16px;
  font-weight: 600;
  color: #fa8c16;
}
.score-total {
  font-size: 12px;
  color: #999;
}
.eval-meta {
  font-size: 12px;
  color: #888;
  flex: 1;
}
.eval-comment {
  margin-top: 4px;
  font-size: 13px;
  color: #444;
  padding-left: 4px;
}
</style>
