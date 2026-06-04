<template>
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px">
      <a-typography-title :level="4" style="margin:0">产品库</a-typography-title>
      <a-button
        v-if="auth.hasRole('super_admin', 'boss', 'purchaser')"
        type="primary"
        @click="openImportDrawer"
      >
        导入库存文件
      </a-button>
    </div>

    <a-row :gutter="12" style="margin-bottom:16px">
      <a-col :span="5">
        <a-select v-model:value="filters.warehouse" style="width:100%" @change="loadData">
          <a-select-option :value="null">全部仓库</a-select-option>
          <a-select-option value="南货场">南货场</a-select-option>
          <a-select-option value="图片小管">图片小管</a-select-option>
          <a-select-option value="库存货场">库存货场</a-select-option>
        </a-select>
      </a-col>
      <a-col :span="5">
        <a-select v-model:value="filters.material" placeholder="材质" allow-clear style="width:100%" @change="loadData">
          <a-select-option value="20#">20#</a-select-option>
          <a-select-option value="45#">45#</a-select-option>
          <a-select-option value="Q345B">Q345B</a-select-option>
          <a-select-option value="42CrMoA">42CrMoA</a-select-option>
        </a-select>
      </a-col>
      <a-col :span="6">
        <a-input-search
          v-model:value="filters.spec"
          placeholder="搜索规格，如 63.5*12"
          allow-clear
          @search="loadData"
          @clear="loadData"
        />
      </a-col>
    </a-row>

    <div style="margin-bottom:12px; display:flex; gap:16px; font-size:13px">
      <span><span style="color:#1677ff">■</span> 南货场</span>
      <span><span style="color:#52c41a">■</span> 图片小管</span>
      <span><span style="color:#fa8c16">■</span> 库存货场</span>
    </div>

    <a-table
      :components="tableComponents"
      :columns="resizableColumns"
      :data-source="products"
      :loading="loading"
      :pagination="{ pageSize: 50, showSizeChanger: true, showTotal: t => `共 ${t} 条` }"
      :scroll="{ x: 'max-content' }"
      :custom-row="customRow"
      row-key="id"
      size="small"
      bordered
    />

    <a-drawer
      v-model:open="importDrawerOpen"
      title="导入库存文件"
      width="420"
      :destroy-on-close="true"
    >
      <a-alert
        message="上传后将清空该仓库旧数据，重新导入。"
        type="warning"
        show-icon
        style="margin-bottom:24px"
      />
      <a-form layout="vertical">
        <a-form-item label="选择仓库" required>
          <a-select v-model:value="importWarehouse" placeholder="请选择仓库" style="width:100%">
            <a-select-option value="南货场">南货场</a-select-option>
            <a-select-option value="图片小管">图片小管</a-select-option>
            <a-select-option value="库存货场">库存货场</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="上传文件" required>
          <a-upload
            :before-upload="beforeUpload"
            :file-list="fileList"
            :max-count="1"
            accept=".xls,.xlsx"
            @remove="fileList = []"
          >
            <a-button><upload-outlined /> 选择文件</a-button>
          </a-upload>
          <div style="color:#999; font-size:12px; margin-top:4px">支持 .xls / .xlsx</div>
        </a-form-item>
        <a-button
          type="primary"
          block
          :loading="importing"
          :disabled="!importWarehouse || fileList.length === 0"
          @click="doImport"
        >
          确认导入
        </a-button>
      </a-form>
      <a-result
        v-if="importResult"
        status="success"
        :title="`导入成功`"
        :sub-title="`${importResult.warehouse} 共导入 ${importResult.imported} 条记录，价格更新日期：${importResult.price_updated_at}`"
        style="margin-top:24px"
      >
        <template #extra>
          <a-button @click="importDrawerOpen = false">关闭</a-button>
        </template>
      </a-result>
    </a-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { message } from 'ant-design-vue'
import { UploadOutlined } from '@ant-design/icons-vue'
import { productsApi } from '@/api/products'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const products = ref([])
const filters = ref({ warehouse: null, material: '20#', spec: '' })

const importDrawerOpen = ref(false)
const importWarehouse = ref(undefined)
const fileList = ref([])
const importing = ref(false)
const importResult = ref(null)

const WAREHOUSE_COLOR = {
  '南货场': '#1677ff',
  '图片小管': '#52c41a',
  '库存货场': '#fa8c16',
}

// 列宽状态
const colWidths = ref({
  warehouse: 90, material: 70, spec: 150, product_type: 100,
  manufacturer: 90, unit_price: 120,
  weight_ton: 80, quantity_pcs: 70, price_updated_at: 110, remark: 160,
})

// 拖拽列宽组件
const ResizableTitle = (props, { slots }) => {
  const { onResize, width, ...thProps } = props
  if (!onResize) return h('th', thProps, slots.default?.())

  return h('th', thProps, [
    slots.default?.(),
    h('span', {
      class: 'col-resize-handle',
      onMousedown: (e) => {
        e.preventDefault()
        const startX = e.clientX
        const startW = width
        const onMove = (me) => {
          const newW = Math.max(50, startW + me.clientX - startX)
          onResize(newW)
        }
        const cleanup = () => {
          window.removeEventListener('mousemove', onMove)
          window.removeEventListener('mouseup', cleanup)
          window.removeEventListener('mouseleave', cleanup)
        }
        window.addEventListener('mousemove', onMove)
        window.addEventListener('mouseup', cleanup)
        window.addEventListener('mouseleave', cleanup)
      },
    }),
  ])
}

const tableComponents = { header: { cell: ResizableTitle } }

const baseColumns = [
  { title: '仓库', dataIndex: 'warehouse', key: 'warehouse', fixed: 'left' },
  { title: '材质', dataIndex: 'material', key: 'material' },
  { title: '规格', dataIndex: 'spec', key: 'spec' },
  { title: '品类', dataIndex: 'product_type', key: 'product_type' },
  { title: '厂家', dataIndex: 'manufacturer', key: 'manufacturer',
    customRender: ({ text }) => text || '' },
  { title: '单价（元/吨）', dataIndex: 'unit_price', key: 'unit_price', align: 'right',
    customRender: ({ text }) => text != null ? h('b', Number(text).toLocaleString()) : '' },
  { title: '吨数', dataIndex: 'weight_ton', key: 'weight_ton', align: 'right',
    customRender: ({ text }) => text != null ? Number(text).toFixed(3) : '' },
  { title: '支数', dataIndex: 'quantity_pcs', key: 'quantity_pcs', align: 'right',
    customRender: ({ text }) => text != null ? text : '' },
  { title: '价格更新日期', dataIndex: 'price_updated_at', key: 'price_updated_at',
    customRender: ({ text }) => text || '' },
  { title: '备注', dataIndex: 'remark', key: 'remark', ellipsis: true,
    customRender: ({ text }) => text || '' },
]

const resizableColumns = computed(() =>
  baseColumns.map((col) => ({
    ...col,
    width: colWidths.value[col.key],
    onHeaderCell: () => ({
      width: colWidths.value[col.key],
      onResize: (w) => { colWidths.value[col.key] = w },
    }),
  }))
)

function customRow(record) {
  return { style: { color: WAREHOUSE_COLOR[record.warehouse] || '#000' } }
}

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.warehouse) params.warehouse = filters.value.warehouse
    if (filters.value.material) params.material = filters.value.material
    if (filters.value.spec) params.spec = filters.value.spec
    const res = await productsApi.list(params)
    products.value = res.data
  } finally {
    loading.value = false
  }
}

function openImportDrawer() {
  importWarehouse.value = undefined
  fileList.value = []
  importResult.value = null
  importDrawerOpen.value = true
}

function beforeUpload(file) {
  fileList.value = [file]
  return false
}

async function doImport() {
  if (!importWarehouse.value || fileList.value.length === 0) return
  importing.value = true
  importResult.value = null
  try {
    const res = await productsApi.importWarehouse(importWarehouse.value, fileList.value[0])
    importResult.value = res.data
    message.success(`导入成功：${res.data.imported} 条`)
    fileList.value = []
    importWarehouse.value = undefined
    loadData()
  } catch {
    // 错误已由 axios 拦截器统一提示
  } finally {
    importing.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.col-resize-handle {
  position: absolute;
  right: -4px;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: col-resize;
  z-index: 1;
}
:deep(th) {
  position: relative;
}
</style>
