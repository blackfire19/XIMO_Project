<template>
  <div>
    <div class="page-header">
      <a-typography-title :level="4" style="margin: 0">用户管理</a-typography-title>
      <a-button type="primary" @click="openCreate">
        <template #icon><plus-outlined /></template>
        新建用户
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="users"
      :loading="loading"
      row-key="id"
      :pagination="{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'role'">
          <a-tag :color="roleColor(record.role.name)">{{ record.role.label }}</a-tag>
        </template>

        <template v-else-if="column.key === 'is_active'">
          <a-badge
            :status="record.is_active ? 'success' : 'default'"
            :text="record.is_active ? '正常' : '已禁用'"
          />
        </template>

        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-button size="small" @click="openEdit(record)">编辑</a-button>
            <a-popconfirm
              :title="record.is_active ? '确认禁用该账号？' : '确认启用该账号？'"
              @confirm="handleToggle(record)"
            >
              <a-button size="small" :danger="record.is_active">
                {{ record.is_active ? '禁用' : '启用' }}
              </a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 新建/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingUser ? '编辑用户' : '新建用户'"
      :confirm-loading="saving"
      @ok="handleSubmit"
      @cancel="resetForm"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical" style="margin-top: 16px">
        <a-form-item label="用户名" name="username" v-if="!editingUser">
          <a-input v-model:value="form.username" placeholder="登录用户名，创建后不可修改" />
        </a-form-item>

        <a-form-item label="姓名" name="full_name">
          <a-input v-model:value="form.full_name" />
        </a-form-item>

        <a-form-item label="角色" name="role_id">
          <a-select v-model:value="form.role_id" placeholder="请选择角色">
            <a-select-option v-for="r in roles" :key="r.id" :value="r.id">
              {{ r.label }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item
          label="业务员编码"
          name="salesperson_code"
          :help="isSalesperson ? '唯一标识，用于生成单号（大写字母/数字）' : ''"
        >
          <a-input
            v-model:value="form.salesperson_code"
            :disabled="!isSalesperson"
            placeholder="仅业务员需要填写"
            style="text-transform: uppercase"
            @input="form.salesperson_code = form.salesperson_code?.toUpperCase()"
          />
        </a-form-item>

        <a-form-item
          :label="editingUser ? '重置密码（留空不修改）' : '密码'"
          name="password"
        >
          <a-input-password v-model:value="form.password" autocomplete="new-password" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { usersApi } from '@/api/users'

const users = ref([])
const roles = ref([])
const loading = ref(false)
const saving = ref(false)
const modalVisible = ref(false)
const editingUser = ref(null)
const formRef = ref()

const form = reactive({
  username: '',
  full_name: '',
  role_id: undefined,
  salesperson_code: '',
  password: '',
})

const isSalesperson = computed(() => {
  const r = roles.value.find((r) => r.id === form.role_id)
  return r?.name === 'salesperson'
})

const rules = computed(() => ({
  username: editingUser.value ? [] : [{ required: true, message: '请输入用户名' }],
  full_name: [{ required: true, message: '请输入姓名' }],
  role_id: [{ required: true, message: '请选择角色' }],
  salesperson_code: isSalesperson.value
    ? [{ required: true, message: '业务员必须填写编码' }]
    : [],
  password: editingUser.value
    ? []
    : [{ required: true, message: '请输入密码' }],
}))

const columns = [
  { title: '姓名', dataIndex: 'full_name', key: 'full_name' },
  { title: '用户名', dataIndex: 'username', key: 'username' },
  { title: '角色', key: 'role' },
  { title: '业务员编码', dataIndex: 'salesperson_code', key: 'salesperson_code' },
  { title: '状态', key: 'is_active' },
  { title: '操作', key: 'actions', width: 150 },
]

function roleColor(name) {
  return { super_admin: 'red', boss: 'blue', salesperson: 'green', purchaser: 'orange' }[name] || 'default'
}

async function loadData() {
  loading.value = true
  try {
    const [uRes, rRes] = await Promise.all([usersApi.list(), usersApi.roles()])
    users.value = uRes.data
    roles.value = rRes.data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingUser.value = null
  resetForm()
  modalVisible.value = true
}

function openEdit(record) {
  editingUser.value = record
  form.username = record.username
  form.full_name = record.full_name
  form.role_id = record.role.id
  form.salesperson_code = record.salesperson_code || ''
  form.password = ''
  modalVisible.value = true
}

function resetForm() {
  form.username = ''
  form.full_name = ''
  form.role_id = undefined
  form.salesperson_code = ''
  form.password = ''
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const payload = {
      full_name: form.full_name,
      role_id: form.role_id,
      salesperson_code: isSalesperson.value ? form.salesperson_code : null,
      password: form.password || undefined,
    }

    if (editingUser.value) {
      await usersApi.update(editingUser.value.id, payload)
      message.success('用户信息已更新')
    } else {
      await usersApi.create({ username: form.username, ...payload })
      message.success('用户已创建')
    }

    modalVisible.value = false
    await loadData()
  } finally {
    saving.value = false
  }
}

async function handleToggle(record) {
  try {
    await usersApi.toggleActive(record.id)
    message.success(record.is_active ? '已禁用' : '已启用')
    await loadData()
  } catch {
    // 错误由 api 拦截器统一处理
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>
