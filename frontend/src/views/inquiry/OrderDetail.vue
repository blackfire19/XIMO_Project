<template>
  <div v-if="order">
    <a-page-header :title="order.subject || order.so_number" @back="$router.back()">
      <template #tags>
        <a-tag :color="STATUS_COLOR[order.status]">{{ STATUS_LABEL[order.status] }}</a-tag>
        <a-tag :color="order.is_stock ? 'blue' : 'gold'">{{ order.is_stock ? '现货' : '非现货' }}</a-tag>
      </template>
      <template #extra>
        <a-button v-if="canEdit" @click="openSubject">编辑主题</a-button>
        <a-popconfirm
          v-if="canEdit && nextStatus"
          :title="advanceTitle"
          @confirm="advance"
        >
          <a-button type="primary">推进到「{{ STATUS_LABEL[nextStatus] }}」</a-button>
        </a-popconfirm>
      </template>
      <a-descriptions size="small" :column="3">
        <a-descriptions-item label="订单编号">{{ order.so_number }}</a-descriptions-item>
        <a-descriptions-item label="客户">{{ fmtCustomer(order.customer?.contact_name, order.customer?.company_name) }}</a-descriptions-item>
        <a-descriptions-item label="业务员">{{ order.salesperson.full_name }}</a-descriptions-item>
        <a-descriptions-item label="创建时间">{{ (order.created_at || '').slice(0,10) }}</a-descriptions-item>
        <a-descriptions-item v-if="!order.is_stock" label="预计生产完成">
          {{ order.est_production_date || '未设置' }}
        </a-descriptions-item>
        <a-descriptions-item label="备注">{{ order.remarks || '—' }}</a-descriptions-item>
        <a-descriptions-item v-if="order.profit != null" label="本单利润（CNY）">
          <span :style="{ fontWeight: 700, color: order.profit >= 0 ? '#52c41a' : '#ff4d4f' }">
            {{ order.profit.toFixed(2) }}
          </span>
        </a-descriptions-item>
      </a-descriptions>
    </a-page-header>

    <!-- 生产倒计时 -->
    <a-alert
      v-if="!order.is_stock && countdown !== null && order.status !== 'completed'"
      :type="countdown < 0 ? 'error' : (countdown <= 7 ? 'warning' : 'info')"
      show-icon
      style="margin:16px 0"
      :message="countdown < 0
        ? `生产已超期 ${-countdown} 天，请尽快跟进`
        : `距预计生产完成还有 ${countdown} 天`"
    />

    <!-- 整页两栏：左栏全部内容，右栏提单信息（贯穿全高） -->
    <a-row :gutter="16" class="main-row">
      <!-- 左栏：全部内容 -->
      <a-col :span="16">
        <!-- 节点提醒（提示该节点需准备的文件） -->
        <a-alert v-if="!isLogistics" :type="reminder.type" show-icon style="margin-bottom:16px" :message="reminder.title">
          <template #description>
            <ul style="margin:4px 0 0; padding-left:18px">
              <li v-for="(item, i) in reminder.items" :key="i" :style="{ color: item.done ? '#52c41a' : '#fa541c' }">
                {{ item.done ? '✓' : '○' }} {{ item.text }}
              </li>
            </ul>
          </template>
        </a-alert>

        <!-- 来自询价单的文件（核价单 / PI 最新版本，只读） -->
        <a-card v-if="!isLogistics" size="small" title="询价单文件（核价单 / PI 最新版本）">
          <template #extra>
            <a-button type="link" size="small"
              @click="$router.push({ name: 'InquiryDetail', params: { id: order.inquiry_id } })">
              查看询价单 →
            </a-button>
          </template>
          <a-empty v-if="!order.inquiry_files || order.inquiry_files.length === 0"
            :image="emptyImage" description="询价单暂无核价单 / PI" />
          <a-list v-else size="small" :data-source="order.inquiry_files" style="max-height:260px; overflow-y:auto">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <a-tag :color="item.doc_type === 'pricing_sheet' ? 'blue' : 'purple'">
                      {{ item.doc_type === 'pricing_sheet' ? '核价单' : 'PI' }}
                    </a-tag>
                    <a :href="`/uploads/${item.file_path}`" target="_blank">{{ item.file_name }}</a>
                    <a-tag color="green" style="margin-left:8px">v{{ item.version }}</a-tag>
                  </template>
                  <template #description>{{ (item.uploaded_at || '').slice(0,10) }}</template>
                </a-list-item-meta>
              </a-list-item>
            </template>
          </a-list>
        </a-card>

    <!-- 文件归档 + 财务/后勤单据：左右分区，等高 -->
    <a-row :gutter="8" class="doc-row-wrap">
      <!-- 文件归档 -->
      <a-col v-if="!isLogistics" :span="12">
        <a-card size="small" title="文件归档" class="doc-card">
          <template #extra>
            <span class="doc-count">已上传 {{ archiveUploadedCount }}/{{ DOC_DEFS.length }}</span>
          </template>
          <a-alert v-if="locked" type="info" show-icon banner :message="lockNotice" />
          <div class="doc-list">
            <div v-for="dt in DOC_DEFS" :key="dt.key" class="doc-row">
              <span class="doc-dot" :class="has(dt.key) ? 'on' : 'off'">{{ has(dt.key) ? '✓' : '' }}</span>
              <a v-if="has(dt.key)" class="doc-name doc-name-link" @click="openFilesModal(dt, canManageDoc(dt.key))">{{ dt.label }}</a>
              <span v-else class="doc-name">{{ dt.label }}</span>
              <span class="doc-files">
                <a v-if="has(dt.key)" class="doc-uploaded" @click="openFilesModal(dt, canManageDoc(dt.key))">已上传 {{ filesByType[dt.key].length }} 个</a>
                <span v-else class="doc-none">未上传</span>
              </span>
              <span class="doc-actions">
                <a-upload v-if="canManageDoc(dt.key)" :before-upload="(f) => beforeUpload(f, dt.key)" :show-upload-list="false">
                  <a class="doc-up">上传</a>
                </a-upload>
              </span>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- 财务 / 后勤单据（非后勤角色：业务员上传，财务后勤下载查看，不受出运锁定） -->
      <a-col v-if="!isLogistics" :span="12">
        <a-card size="small" title="财务 / 后勤单据" class="doc-card">
          <template #extra>
            <span class="doc-count">已上传 {{ finUploadedCount }}/{{ visibleFinDocs.length }}</span>
          </template>
          <div class="doc-list">
            <div v-for="dt in visibleFinDocs" :key="dt.key" class="doc-row">
              <span class="doc-dot" :class="has(dt.key) ? 'on' : 'off'">{{ has(dt.key) ? '✓' : '' }}</span>
              <a v-if="has(dt.key)" class="doc-name doc-name-link" @click="openFilesModal(dt, canManageFinCard(dt.key))">{{ dt.label }}</a>
              <span v-else class="doc-name">{{ dt.label }}</span>
              <span class="doc-files">
                <a v-if="has(dt.key)" class="doc-uploaded" @click="openFilesModal(dt, canManageFinCard(dt.key))">已上传 {{ filesByType[dt.key].length }} 个</a>
                <span v-else class="doc-none">未上传</span>
              </span>
              <span class="doc-actions">
                <a-upload v-if="canManageFinCard(dt.key)" :before-upload="(f) => beforeUpload(f, dt.key)" :show-upload-list="false">
                  <a class="doc-up">上传</a>
                </a-upload>
              </span>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- 后勤视角：随附单据（CI/MTC/PL，只读查看） -->
      <a-col v-if="isLogistics" :span="24" class="logi-stack">
        <a-card size="small" title="随附单据" class="doc-card">
          <template #extra>
            <span class="doc-count">已上传 {{ attachedUploadedCount }}/{{ attachedDocs.length }}</span>
          </template>
          <div class="att-grid">
            <div v-for="dt in attachedDocs" :key="dt.key" class="att-doc" :class="{ done: has(dt.key) }">
              <div class="att-head">
                <span class="att-title">
                  <check-circle-filled v-if="has(dt.key)" class="logi-ok" />
                  {{ dt.label }}
                </span>
                <a-tag :color="has(dt.key) ? 'success' : 'default'" :bordered="false">
                  {{ has(dt.key) ? '已上传' : '未上传' }}
                </a-tag>
              </div>

              <template v-if="has(dt.key)">
                <div class="att-thumb">
                  <a-image
                    v-if="isImage(filesByType[dt.key][0].file_name)"
                    :src="`/uploads/${filesByType[dt.key][0].file_path}`"
                    :width="96"
                    :height="96"
                    class="att-thumb-img"
                  />
                  <a v-else :href="`/uploads/${filesByType[dt.key][0].file_path}`" target="_blank" class="att-thumb-file" :title="`预览 ${filesByType[dt.key][0].file_name}`">
                    <file-pdf-outlined v-if="isPdf(filesByType[dt.key][0].file_name)" />
                    <file-text-outlined v-else />
                  </a>
                </div>
                <div class="att-file-row">
                  <a :href="`/uploads/${filesByType[dt.key][0].file_path}`" target="_blank" class="att-file-name" :title="filesByType[dt.key][0].file_name">
                    {{ filesByType[dt.key][0].file_name }}
                  </a>
                  <a :href="`/uploads/${filesByType[dt.key][0].file_path}`" :download="filesByType[dt.key][0].file_name" class="att-dl">下载</a>
                </div>
              </template>
              <div v-else class="att-empty">未上传</div>
            </div>
          </div>
        </a-card>

        <!-- 后勤视角：后勤单据（出口许可证 / CO，卡片式拖拽上传） -->
        <a-card size="small" title="后勤单据" class="doc-card logi-card" style="margin-top:8px">
          <template #extra>
            <span class="doc-count">已上传 {{ logiUploadedCount }}/{{ logisticsDocs.length }}</span>
          </template>
          <div class="logi-grid">
            <div v-for="dt in logisticsDocs" :key="dt.key" class="att-doc" :class="{ done: has(dt.key) }">
              <div class="att-head">
                <span class="att-title">
                  <check-circle-filled v-if="has(dt.key)" class="logi-ok" />
                  {{ dt.label }}
                </span>
                <a-tag :color="has(dt.key) ? 'success' : 'default'" :bordered="false">
                  {{ has(dt.key) ? '已上传' : '未上传' }}
                </a-tag>
              </div>

              <!-- 已上传：单文件缩略图 + 文件名 + 删除（删除后才能重新上传） -->
              <template v-if="has(dt.key)">
                <div class="att-thumb">
                  <a-image
                    v-if="isImage(filesByType[dt.key][0].file_name)"
                    :src="`/uploads/${filesByType[dt.key][0].file_path}`"
                    :width="96"
                    :height="96"
                    class="att-thumb-img"
                  />
                  <a v-else :href="`/uploads/${filesByType[dt.key][0].file_path}`" target="_blank" class="att-thumb-file" :title="`预览 ${filesByType[dt.key][0].file_name}`">
                    <file-pdf-outlined v-if="isPdf(filesByType[dt.key][0].file_name)" />
                    <file-text-outlined v-else />
                  </a>
                </div>
                <div class="att-file-row">
                  <a :href="`/uploads/${filesByType[dt.key][0].file_path}`" target="_blank" class="att-file-name" :title="filesByType[dt.key][0].file_name">
                    {{ filesByType[dt.key][0].file_name }}
                  </a>
                  <a-popconfirm
                    v-if="canManageFinCard(dt.key)"
                    title="删除后可重新上传，确认删除？"
                    ok-text="删除"
                    cancel-text="取消"
                    @confirm="delFile(filesByType[dt.key][0].id)"
                  >
                    <delete-outlined class="att-del" />
                  </a-popconfirm>
                </div>
              </template>

              <!-- 未上传：拖拽上传区（仅在无文件时显示） -->
              <a-upload-dragger
                v-else-if="canManageFinCard(dt.key)"
                :before-upload="(f) => beforeUpload(f, dt.key)"
                :show-upload-list="false"
                class="logi-dragger"
                accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.bmp,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
              >
                <p class="logi-drag-icon"><inbox-outlined /></p>
                <p class="logi-drag-text">点击或拖拽文件到此处上传</p>
                <p class="logi-drag-hint">支持 PDF、图片及 Office 文档</p>
              </a-upload-dragger>
              <div v-else class="att-empty">暂无文件</div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 补充附件（出运锁定后显示，用于补充说明） -->
    <a-card v-if="locked && !isLogistics" size="small" title="补充附件（补充说明，不受出运锁定限制）" style="margin-top:8px">
      <template #extra>
        <a-popconfirm
          v-if="canSupplement"
          title="补充附件上传后不可删除，确认上传？"
          ok-text="确认上传"
          cancel-text="取消"
          @confirm="triggerSupplementUpload"
        >
          <a-button type="link" size="small">上传补充附件</a-button>
        </a-popconfirm>
        <input ref="supplementInputRef" type="file" style="display:none" @change="onSupplementFileChange" />
      </template>
      <a-empty v-if="!filesByType.supplement || filesByType.supplement.length === 0"
        :image="emptyImage" description="暂无补充附件" />
      <a-list v-else size="small" :data-source="filesByType.supplement" style="max-height:260px; overflow-y:auto">
        <template #renderItem="{ item }">
          <a-list-item>
            <a :href="`/uploads/${item.file_path}`" target="_blank">{{ item.file_name }}</a>
            <span style="color:#999; margin-left:12px">{{ (item.uploaded_at || '').slice(0,10) }}</span>
          </a-list-item>
        </template>
      </a-list>
    </a-card>

    <!-- 提单 编辑/创建 modal -->
    <a-modal v-model:open="blOpen" :title="blEditing ? '编辑提单' : '创建提单'" :width="640" :confirm-loading="saving" @ok="submitBL" @cancel="blEditing = false">
      <a-form v-if="blForm" layout="vertical">
        <a-form-item label="运输方式">
          <a-radio-group v-model:value="blForm.ship_type">
            <a-radio value="container">集装箱</a-radio>
            <a-radio value="bulk">散货船</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12"><a-form-item label="船司"><a-input v-model:value="blForm.carrier" placeholder="如 MAERSK、COSCO" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="提单号" required><a-input v-model:value="blForm.bl_number" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="船名航次"><a-input v-model:value="blForm.vessel_voyage" /></a-form-item></a-col>
          <a-col :span="12">
            <a-form-item label="目的国" required>
              <a-select
                v-model:value="blForm.discharge_country"
                show-search
                allow-clear
                placeholder="搜索国家（中文或英文）"
                :filter-option="false"
                :options="countryOptions"
                @search="onCountrySearch"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12"><a-form-item label="起运港" required><a-input v-model:value="blForm.load_port" placeholder="如 Shanghai" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="目的港" required><a-input v-model:value="blForm.discharge_port" placeholder="如 Hamburg" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="ETD"><a-date-picker v-model:value="blForm.etd" style="width:100%" value-format="YYYY-MM-DD" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="ETA"><a-date-picker v-model:value="blForm.eta" style="width:100%" value-format="YYYY-MM-DD" /></a-form-item></a-col>
          <a-col v-if="blForm.ship_type === 'container'" :span="24">
            <a-form-item label="箱型箱量">
              <a-input v-model:value="blForm.container_info" placeholder="如 20GP*2，40HC*1" />
            </a-form-item>
          </a-col>
        </a-row>

        <template v-if="blForm.ship_type === 'bulk'">
          <a-row :gutter="12">
            <a-col :span="8"><a-form-item label="件数"><a-input-number v-model:value="blForm.pieces" style="width:100%" :min="0" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="重量(MT)"><a-input-number v-model:value="blForm.weight_mt" style="width:100%" :min="0" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="体积(CBM)"><a-input-number v-model:value="blForm.volume_cbm" style="width:100%" :min="0" /></a-form-item></a-col>
          </a-row>
        </template>

        <a-form-item label="备注"><a-textarea v-model:value="blForm.remarks" :rows="2" /></a-form-item>
      </a-form>
    </a-modal>

    <!-- 单据附件 查看 modal（点击文件名打开，展示该单据全部附件） -->
    <a-modal
      v-model:open="filesModalOpen"
      :title="filesModalDoc ? `${filesModalDoc.label} — 已上传附件` : '已上传附件'"
      :footer="null"
      :width="560"
    >
      <a-list
        size="small"
        :data-source="filesModalDoc ? (filesByType[filesModalDoc.key] || []) : []"
        :locale="{ emptyText: '暂无附件' }"
      >
        <template #renderItem="{ item }">
          <a-list-item>
            <span class="modal-file-name">
              <a v-if="isPreviewable(item.file_name)" :href="`/uploads/${item.file_path}`" target="_blank">{{ item.file_name }}</a>
              <a v-else :href="`/uploads/${item.file_path}`" :download="item.file_name">{{ item.file_name }}</a>
            </span>
            <template #actions>
              <a v-if="isPreviewable(item.file_name)" :href="`/uploads/${item.file_path}`" target="_blank">预览</a>
              <a :href="`/uploads/${item.file_path}`" :download="item.file_name">下载</a>
              <a-popconfirm v-if="filesModalDoc && filesModalDoc.canManage" title="确认删除该附件？" @confirm="delFile(item.id)">
                <a style="color:#ff4d4f">删除</a>
              </a-popconfirm>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </a-modal>

    <!-- 订单主题 编辑 modal -->
    <a-modal v-model:open="subjectOpen" title="编辑订单主题" :confirm-loading="subjectSaving" @ok="saveSubject">
      <a-form layout="vertical">
        <a-form-item label="主题" required help="必填，列表将直接显示该主题">
          <a-input v-model:value="subjectInput" :maxlength="120" show-count placeholder="如：德国客户 H 型钢首单" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 财务记账（仅财务角色，且仅已完结订单） -->
    <a-card
      v-if="order && order.status === 'completed' && auth.hasRole('finance')"
      size="small"
      title="财务记账"
      style="margin-top: 16px"
    >
      <template #extra>
        <a-space>
          <template v-if="accountingRecord">
            <a-tag v-if="accountingRecord.salary_calculated" color="green" style="font-size:13px; padding:3px 10px">
              已发放工资 ✓
            </a-tag>
            <a-popconfirm
              v-else
              title="确认标记为已发放工资？一旦标记将无法撤销。"
              ok-text="确认标记"
              cancel-text="取消"
              @confirm="toggleSalary"
            >
              <a-button size="small" type="primary" ghost>标记工资发放</a-button>
            </a-popconfirm>
          </template>
          <a-button v-if="!salaryLocked" type="primary" size="small" @click="openAccounting">
            {{ accountingRecord ? '编辑记账' : '记录利润' }}
          </a-button>
        </a-space>
      </template>

      <a-empty v-if="!accountingRecord" :image="emptyImage" description="暂无记账记录" />
      <a-descriptions v-else size="small" :column="3" bordered>
        <a-descriptions-item label="本单利润（CNY）">
          <span :style="{ fontWeight: 700, color: accountingRecord.profit == null ? '#999' : accountingRecord.profit >= 0 ? '#52c41a' : '#ff4d4f' }">
            {{ accountingRecord.profit != null ? accountingRecord.profit.toFixed(2) : '—' }}
          </span>
        </a-descriptions-item>
        <a-descriptions-item label="工资发放">
          <a-tag :color="accountingRecord.salary_calculated ? 'green' : 'default'">
            {{ accountingRecord.salary_calculated ? '已发放' : '未发放' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="记账人">{{ accountingRecord.recorder_name }}</a-descriptions-item>
        <a-descriptions-item label="记账时间">{{ (accountingRecord.recorded_at || '').slice(0, 10) }}</a-descriptions-item>
        <a-descriptions-item v-if="accountingRecord.notes" label="备注" :span="3">{{ accountingRecord.notes }}</a-descriptions-item>
        <a-descriptions-item label="附件" :span="3">
          <template v-if="accountingRecord.file_name">
            <a :href="`/uploads/${accountingRecord.file_path}`" target="_blank">{{ accountingRecord.file_name }}</a>
            <a-popconfirm title="删除附件？" @confirm="deleteAccountingFile">
              <a style="color:#ff4d4f; margin-left:12px">删除</a>
            </a-popconfirm>
          </template>
          <span v-else style="color:#bbb">无附件</span>
        </a-descriptions-item>
      </a-descriptions>
    </a-card>

    <!-- 记账 Modal -->
    <a-modal
      v-model:open="accountingOpen"
      title="财务记账"
      :confirm-loading="accountingSaving"
      ok-text="保存"
      cancel-text="取消"
      @ok="submitAccounting"
    >
      <a-form layout="vertical">
        <a-form-item label="本单利润（CNY）" required>
          <a-input-number
            v-model:value="accountingForm.profit"
            style="width:100%"
            :precision="2"
            placeholder="可为负数"
            addon-after="CNY"
          />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="accountingForm.notes" :rows="3" placeholder="选填" />
        </a-form-item>
        <a-form-item label="上传凭证文件（选填）">
          <a-upload
            :before-upload="onPickFile"
            :file-list="accountingFileList"
            :max-count="1"
            @remove="accountingFileList = []"
          >
            <a-button size="small">选择文件</a-button>
          </a-upload>
          <div v-if="accountingRecord?.file_name && accountingFileList.length === 0" style="margin-top:4px;color:#999;font-size:12px">
            已有附件：{{ accountingRecord.file_name }}（不重新上传则保留原附件）
          </div>
        </a-form-item>
      </a-form>
    </a-modal>

      </a-col>

      <!-- 右栏：提单信息 + 评价记录 -->
      <a-col :span="8">
        <a-card size="small" title="提单信息" class="bl-card">
          <template #extra>
            <a-space v-if="canEdit">
              <a-button v-if="!bl" type="primary" size="small" @click="openBL(false)">创建提单</a-button>
              <template v-else>
                <a-button size="small" @click="openBL(true)">编辑</a-button>
                <a-popconfirm title="删除提单将同时删除其下集装箱，确认？" @confirm="delBL">
                  <a-button size="small" danger>删除</a-button>
                </a-popconfirm>
              </template>
            </a-space>
          </template>

          <a-empty v-if="!bl" :image="emptyImage" description="暂无提单信息" />
          <a-descriptions v-else size="small" :column="1" bordered>
            <a-descriptions-item label="运输方式">
              <a-tag :color="bl.ship_type === 'bulk' ? 'purple' : 'blue'">
                {{ bl.ship_type === 'bulk' ? '散货船' : '集装箱' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="船司">{{ bl.carrier || '—' }}</a-descriptions-item>
            <a-descriptions-item label="提单号">{{ bl.bl_number || '—' }}</a-descriptions-item>
            <a-descriptions-item v-if="bl.ship_type === 'container'" label="箱型箱量">{{ bl.container_info || '—' }}</a-descriptions-item>
            <a-descriptions-item label="状态">
              <a-select
                v-if="canEdit"
                :value="bl.status"
                size="small"
                style="width:120px"
                @change="(v) => changeBLStatus(v)"
              >
                <a-select-option v-for="(l, k) in BL_STATUS_LABEL" :key="k" :value="k">{{ l }}</a-select-option>
              </a-select>
              <span v-else>{{ BL_STATUS_LABEL[bl.status] }}</span>
            </a-descriptions-item>
            <a-descriptions-item label="船名航次">{{ bl.vessel_voyage || '—' }}</a-descriptions-item>
            <a-descriptions-item label="起运港">{{ bl.load_port || '—' }}</a-descriptions-item>
            <a-descriptions-item label="目的港">{{ bl.discharge_port || '—' }}</a-descriptions-item>
            <a-descriptions-item label="目的国">{{ bl.discharge_country ? countryLabel(bl.discharge_country) : '—' }}</a-descriptions-item>
            <a-descriptions-item label="ETD">{{ bl.etd || '—' }}</a-descriptions-item>
            <a-descriptions-item label="ETA">{{ bl.eta || '—' }}</a-descriptions-item>
            <a-descriptions-item label="备注">{{ bl.remarks || '—' }}</a-descriptions-item>
            <template v-if="bl.ship_type === 'bulk'">
              <a-descriptions-item label="件数">{{ bl.pieces ?? '—' }}</a-descriptions-item>
              <a-descriptions-item label="重量(MT)">{{ bl.weight_mt ?? '—' }}</a-descriptions-item>
              <a-descriptions-item label="体积(CBM)">{{ bl.volume_cbm ?? '—' }}</a-descriptions-item>
            </template>
          </a-descriptions>
        </a-card>

        <!-- 评价记录 -->
        <a-card v-if="order && !isLogistics" size="small" style="margin-top:16px">
          <EvaluationPanel
            target-type="formal_order"
            :target-id="order.id"
            :subject-id="order.salesperson.id"
          />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { message, Empty } from 'ant-design-vue'
import { InboxOutlined, FileTextOutlined, FilePdfOutlined, DeleteOutlined, CheckCircleFilled } from '@ant-design/icons-vue'
import { formalOrdersApi } from '@/api/inquiries'
import { accountingApi } from '@/api/accounting'
import { useAuthStore } from '@/stores/auth'
import { fmtCustomer } from '@/utils/format'
import { filterCountries, countryLabel } from '@/utils/countries'
import EvaluationPanel from '@/components/EvaluationPanel.vue'

const route = useRoute()
const auth = useAuthStore()
const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE

// 图片 / PDF 可预览，其余只能下载
const PREVIEW_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'pdf']
function isPreviewable(name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  return PREVIEW_EXTS.includes(ext)
}
const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']
function isImage(name) {
  return IMAGE_EXTS.includes((name || '').split('.').pop().toLowerCase())
}
function isPdf(name) {
  return (name || '').split('.').pop().toLowerCase() === 'pdf'
}

const STATUS_LABEL = {
  confirmed: '已确认', production: '生产中', ready: '待出运',
  shipping: '出运中', completed: '已完结',
}
const STATUS_COLOR = {
  confirmed: 'blue', production: 'gold', ready: 'orange',
  shipping: 'cyan', completed: 'green',
}
const BL_STATUS_LABEL = { planned: '计划中', loaded: '已装柜', transit: '运输中', arrived: '已到港' }

const DOC_DEFS = [
  { key: 'ci', label: 'CI 商业发票' },
  { key: 'mtc', label: 'MTC 质保书' },
  { key: 'pl', label: 'PL 装箱单' },
  { key: 'inspection', label: '验货照片' },
  { key: 'packing', label: '装箱照片' },
  { key: 'ocean_bl', label: '海运提单' },
]

// 财务 / 后勤单据区：fin_* 与报关单由业务员上传；出口许可证、CO 沿用各自归档权限
const FIN_DOC_DEFS = [
  { key: 'fin_ci', label: 'CI 商业发票' },
  { key: 'fin_mtc', label: 'MTC 质保书' },
  { key: 'fin_pl', label: 'PL 装箱单' },
  { key: 'customs_declaration', label: '报关单' },
  { key: 'export_permit', label: '出口许可证' },
  { key: 'co', label: 'CO 原产地证' },
]
// 这两项移入本区显示，但权限/锁定沿用归档逻辑（canManageDoc）
const FIN_DOC_ARCHIVE_KEYS = ['export_permit', 'co']

const order = ref(null)
const bl = computed(() => order.value?.bls?.[0] || null)

const salaryLocked = computed(() => !!order.value?.salary_calculated)

const canEdit = computed(() => {
  if (!order.value) return false
  if (salaryLocked.value) return false        // 工资已发放，全员锁定
  if (auth.hasRole('super_admin')) return order.value.status !== 'completed'
  if (auth.hasRole('salesperson')) return order.value.salesperson.id === auth.user?.id && order.value.status !== 'completed'
  return false
})

// CO 原产地证 / 出口许可证：后勤单据，后勤+超管可维护，不受出运/工资核算锁定
// （这两类单据通常出运阶段或出运后才出具，出运中/已完结仍需补传）
const canEditLogisticsDoc = computed(() => auth.hasRole('super_admin', 'logistics'))

// 出运阶段例外：海运提单通常出运后才出具，shipping 状态仍可上传/删除
const SHIPPING_STAGE_DOCS = ['ocean_bl']
function canManageDoc(key) {
  if (key === 'co' || key === 'export_permit') return canEditLogisticsDoc.value
  if (!canEdit.value) return false
  if (!locked.value) return true
  return order.value?.status === 'shipping' && SHIPPING_STAGE_DOCS.includes(key)
}

// 后勤严格受限：仅可见 fin CI/MTC、出口许可证、CO；其余单据区域全部隐藏
const isLogistics = computed(() => auth.hasRole('logistics'))
const visibleFinDocs = computed(() =>
  isLogistics.value
    ? FIN_DOC_DEFS.filter(d => ['fin_ci', 'fin_mtc', 'fin_pl', 'export_permit', 'co'].includes(d.key))
    : FIN_DOC_DEFS
)

// 后勤视角专用分区：随附单据（CI/MTC/PL，后勤只读查看）+ 后勤单据（出口许可证/CO，后勤上传）
const ATTACHED_DOC_KEYS = ['fin_ci', 'fin_mtc', 'fin_pl']
const LOGI_DOC_KEYS = ['export_permit', 'co']
const attachedDocs = computed(() => FIN_DOC_DEFS.filter(d => ATTACHED_DOC_KEYS.includes(d.key)))
const logisticsDocs = computed(() => FIN_DOC_DEFS.filter(d => LOGI_DOC_KEYS.includes(d.key)))

// 财务 / 后勤单据：由业务员上传维护（财务、后勤仅下载查看），不受锁定限制
function canManageFinDoc() {
  if (!order.value) return false
  if (auth.hasRole('super_admin')) return true
  if (auth.hasRole('salesperson')) return order.value.salesperson.id === auth.user?.id
  return false
}

// 财务 / 后勤单据区的上传/删除权限：出口许可证、CO 沿用归档权限，其余走 fin 权限
function canManageFinCard(key) {
  return FIN_DOC_ARCHIVE_KEYS.includes(key) ? canManageDoc(key) : canManageFinDoc()
}

const lockNotice = computed(() =>
  order.value?.status === 'shipping'
    ? '订单已进入出运阶段，归档文件已锁定仅可查看；其中「海运提单」在出运阶段仍可上传/删除，「CO 原产地证」「出口许可证」请在下方「财务 / 后勤单据」区维护。其余如需补充，请使用下方「补充附件」。'
    : '订单已完结，归档文件已锁定，仅可查看。如需补充，请使用下方「补充附件」。'
)

// 核算工资后，非财务仍可上传/删除补充附件
const canSupplement = computed(() => {
  if (!order.value) return false
  if (auth.hasRole('finance', 'logistics')) return false   // 财务核算后完全锁定；后勤只读
  if (salaryLocked.value) return true
  return canEdit.value
})

// 线性流转；现货订单跳过「生产中」
function computeNext(o) {
  if (!o) return null
  switch (o.status) {
    case 'confirmed': return o.is_stock ? 'ready' : 'production'
    case 'production': return 'ready'
    case 'ready': return 'shipping'
    case 'shipping': return 'completed'
    default: return null
  }
}
const nextStatus = computed(() => computeNext(order.value))

const locked = computed(() => ['shipping', 'completed'].includes(order.value?.status))

const advanceTitle = computed(() => {
  if (nextStatus.value === 'shipping') {
    return '推进到「出运中」后，已上传的归档文件将被锁定（仅可查看），仅能上传海运提单、「财务 / 后勤单据」区（CO、出口许可证等）以及补充附件。确认推进？'
  }
  return `确认将订单推进到「${STATUS_LABEL[nextStatus.value]}」？`
})

const countdown = computed(() => {
  if (!order.value?.est_production_date) return null
  const target = new Date(order.value.est_production_date)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((target - today) / 86400000)
})

const filesByType = computed(() => {
  const map = {}
  for (const dt of DOC_DEFS) map[dt.key] = []
  for (const f of order.value?.files || []) {
    if (!map[f.doc_type]) map[f.doc_type] = []
    map[f.doc_type].push(f)
  }
  return map
})
function has(key) { return (filesByType.value[key] || []).length > 0 }

// 紧凑列表顶部「已上传 X/N」计数（无进度条）
const archiveUploadedCount = computed(() => DOC_DEFS.filter(d => has(d.key)).length)
const finUploadedCount = computed(() => visibleFinDocs.value.filter(d => has(d.key)).length)
const attachedUploadedCount = computed(() => attachedDocs.value.filter(d => has(d.key)).length)
const logiUploadedCount = computed(() => logisticsDocs.value.filter(d => has(d.key)).length)

const reminder = computed(() => {
  const s = order.value?.status
  const hasBL = !!bl.value
  if (s === 'confirmed') {
    return {
      type: 'info', title: '已确认 —— 准备投产',
      items: [
        { text: '核对最终 PI、唛头、技术要求', done: false },
        { text: order.value.is_stock ? '现货订单，确认库存已锁定' : '非现货，确认预计生产完成日期已填写', done: order.value.is_stock || !!order.value.est_production_date },
      ],
    }
  }
  if (s === 'production') {
    return {
      type: 'info', title: '生产中 —— 建议归档以下文件',
      items: [
        { text: '验货照片（建议）', done: has('inspection') },
        { text: 'MTC 质保书（可提前归档）', done: has('mtc') },
        { text: '安排验货 / 跟踪生产进度', done: false },
      ],
    }
  }
  if (s === 'ready') {
    return {
      type: has('pl') && has('ci') ? 'success' : 'error',
      title: '待出运 —— 出运前请备齐',
      items: [
        { text: 'PL 装箱单（必备）', done: has('pl') },
        { text: 'CI 商业发票（必备）', done: has('ci') },
        { text: 'CO 原产地证 / 出口许可证（按需）', done: has('co') || has('export_permit') },
        { text: '装箱照片（建议）', done: has('packing') },
        { text: 'MTC 质保书', done: has('mtc') },
      ],
    }
  }
  if (s === 'shipping') {
    return {
      type: hasBL ? 'success' : 'warning',
      title: '出运中 —— 完善提单与集装箱',
      items: [
        { text: '录入提单(BL)信息', done: hasBL },
        { text: '维护起运港 / 目的港、船名航次、ETD/ETA', done: false },
      ],
    }
  }
  return {
    type: 'success', title: '已完结 —— 确认归档完整',
    items: [
      { text: 'MTC 已归档', done: has('mtc') },
      { text: 'PL / CI 已归档', done: has('pl') && has('ci') },
      { text: '提单信息完整', done: hasBL },
    ],
  }
})

// ── 财务记账 ──
const accountingRecord = ref(null)
const accountingOpen = ref(false)
const accountingSaving = ref(false)
const accountingForm = ref({ profit: null, notes: '' })
const accountingFileList = ref([])

async function loadAccounting(orderId) {
  if (!auth.hasRole('finance')) return
  const res = await accountingApi.get(orderId)
  accountingRecord.value = res.status === 404 ? null : res.data
}

function openAccounting() {
  const r = accountingRecord.value
  accountingForm.value = {
    profit: r?.profit ?? null,
    notes: r?.notes ?? '',
  }
  accountingFileList.value = []
  accountingOpen.value = true
}

function onPickFile(file) {
  accountingFileList.value = [file]
  return false
}

async function submitAccounting() {
  const f = accountingForm.value
  if (f.profit === null || f.profit === undefined) {
    message.warning('请填写本单利润')
    return
  }
  accountingSaving.value = true
  try {
    const fd = new FormData()
    fd.append('profit', Math.round(f.profit * 100) / 100)
    if (f.notes) fd.append('notes', f.notes)
    if (accountingFileList.value.length > 0) fd.append('file', accountingFileList.value[0])
    await accountingApi.save(order.value.id, fd)
    message.success('记账记录已保存')
    accountingOpen.value = false
    await loadAccounting(order.value.id)
  } catch {
    // 拦截器已提示
  } finally {
    accountingSaving.value = false
  }
}

async function deleteAccountingFile() {
  await accountingApi.deleteFile(order.value.id)
  message.success('附件已删除')
  await loadAccounting(order.value.id)
}

async function toggleSalary() {
  const res = await accountingApi.toggleSalary(order.value.id)
  accountingRecord.value = res.data
  message.success(res.data.salary_calculated ? '已标记为工资发放' : '已取消核算工资标记')
}

// ── 补充附件（确认后才触发文件选择） ──
const supplementInputRef = ref(null)

function triggerSupplementUpload() {
  supplementInputRef.value?.click()
}

async function onSupplementFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''   // 重置，允许重复选同名文件
  try {
    await formalOrdersApi.uploadFile(order.value.id, 'supplement', file)
    message.success('补充附件上传成功')
    await load()
  } catch { /* 拦截器已提示 */ }
}

async function load() {
  const res = await formalOrdersApi.get(route.params.id)
  order.value = res.data
  if (res.data.status === 'completed') {
    await loadAccounting(res.data.id)
  }
}

async function advance() {
  await formalOrdersApi.setStatus(order.value.id, nextStatus.value)
  message.success('状态已推进')
  await load()
}

// ── 订单主题 ──
const subjectOpen = ref(false)
const subjectSaving = ref(false)
const subjectInput = ref('')

function openSubject() {
  subjectInput.value = order.value.subject || ''
  subjectOpen.value = true
}

async function saveSubject() {
  const subject = subjectInput.value.trim()
  if (!subject) { message.warning('请填写订单主题'); return }
  subjectSaving.value = true
  try {
    await formalOrdersApi.update(order.value.id, { subject })
    message.success('主题已保存')
    subjectOpen.value = false
    await load()
  } finally {
    subjectSaving.value = false
  }
}

async function beforeUpload(file, docType) {
  try {
    await formalOrdersApi.uploadFile(order.value.id, docType, file)
    message.success('上传成功')
    await load()
  } catch { /* 拦截器已提示 */ }
  return false
}

async function delFile(fileId) {
  await formalOrdersApi.deleteFile(order.value.id, fileId)
  message.success('已删除')
  await load()
}

// ── 提单 ──
// 单据附件查看 modal
const filesModalOpen = ref(false)
const filesModalDoc = ref(null) // { key, label, canManage }
function openFilesModal(dt, canManage) {
  if (!has(dt.key)) return
  filesModalDoc.value = { key: dt.key, label: dt.label, canManage }
  filesModalOpen.value = true
}

const blOpen = ref(false)
const blEditing = ref(false)
const saving = ref(false)
const blForm = ref(null)
const countryOptions = ref(filterCountries(''))
function onCountrySearch(val) {
  countryOptions.value = filterCountries(val)
}

function openBL(editing) {
  blEditing.value = editing
  if (editing && bl.value) {
    const b = bl.value
    blForm.value = {
      ship_type: b.ship_type, carrier: b.carrier || '', bl_number: b.bl_number || '', vessel_voyage: b.vessel_voyage || '',
      container_info: b.container_info || '',
      load_port: b.load_port || '', discharge_port: b.discharge_port || '',
      discharge_country: b.discharge_country || undefined,
      etd: b.etd || null, eta: b.eta || null,
      pieces: b.pieces, weight_mt: b.weight_mt, volume_cbm: b.volume_cbm,
      remarks: b.remarks || '',
    }
  } else {
    blForm.value = {
      ship_type: 'container', carrier: '', bl_number: '', vessel_voyage: '',
      container_info: '',
      load_port: '', discharge_port: '', discharge_country: undefined, etd: null, eta: null,
      pieces: null, weight_mt: null, volume_cbm: null, remarks: '',
    }
  }
  blOpen.value = true
}

async function submitBL() {
  const f = blForm.value
  if (!f.bl_number || !f.bl_number.trim()) { message.warning('请填写提单号'); return }
  if (!f.discharge_country) { message.warning('请选择目的国'); return }
  if (!f.discharge_port || !f.discharge_port.trim()) { message.warning('请填写目的港'); return }
  if (!f.load_port || !f.load_port.trim()) { message.warning('请填写起运港'); return }
  saving.value = true
  try {
    const payload = {
      ship_type: f.ship_type,
      carrier: f.carrier || null,
      bl_number: f.bl_number || null,
      vessel_voyage: f.vessel_voyage || null,
      container_info: f.ship_type === 'container' ? (f.container_info || null) : null,
      load_port: f.load_port || null,
      discharge_port: f.discharge_port || null,
      discharge_country: f.discharge_country || null,
      etd: f.etd || null,
      eta: f.eta || null,
      remarks: f.remarks || null,
      pieces: f.ship_type === 'bulk' ? f.pieces : null,
      weight_mt: f.ship_type === 'bulk' ? f.weight_mt : null,
      volume_cbm: f.ship_type === 'bulk' ? f.volume_cbm : null,
    }
    if (blEditing.value) {
      await formalOrdersApi.updateBL(order.value.id, bl.value.id, payload)
      message.success('已更新提单')
    } else {
      await formalOrdersApi.addBL(order.value.id, payload)
      message.success('已创建提单')
    }
    blOpen.value = false
    await load()
  } catch (e) {
    // 错误提示由 api 响应拦截器统一弹出；此处仅捕获以保持弹窗打开供重试
  } finally {
    saving.value = false
  }
}

async function changeBLStatus(status) {
  await formalOrdersApi.updateBL(order.value.id, bl.value.id, { status })
  message.success('状态已更新')
  await load()
}

async function delBL() {
  await formalOrdersApi.deleteBL(order.value.id, bl.value.id)
  message.success('已删除提单')
  await load()
}

onMounted(load)
</script>

<style scoped>
/* 文件归档 / 财务后勤：左右分区等高 */
.doc-row-wrap { margin-top: 8px; }
.doc-row-wrap > .ant-col { display: flex; }
.doc-card { width: 100%; height: 100%; }
/* 紧凑列表：一行一单据 */
.doc-card :deep(.ant-card-body) { padding: 0; }
/* 单据较多时内部滚动 */
.doc-list { max-height: 320px; overflow-y: auto; }
.doc-count { font-size: 13px; color: rgba(0, 0, 0, 0.45); }
.doc-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-top: 1px solid #fafafa;
  transition: background 0.15s;
}
.doc-row:first-child { border-top: none; }
.doc-row:hover { background: #fafbff; }
.doc-dot {
  flex: 0 0 18px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
}
.doc-dot.on { background: #52c41a; color: #fff; }
.doc-dot.off { border: 1.5px solid #ff4d4f; background: #fff; }
.doc-name { flex: 0 0 130px; font-weight: 500; }
.doc-name-link { color: #1677ff; cursor: pointer; }
.doc-name-link:hover { text-decoration: underline; }
.doc-uploaded { color: #52c41a; cursor: pointer; }
.doc-uploaded:hover { text-decoration: underline; }
.modal-file-name { flex: 1 1 auto; min-width: 0; word-break: break-all; }
.doc-files {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.doc-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 1px 8px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
}
.doc-chip a { color: #1677ff; }
.doc-chip-dl { font-size: 12px; }
.doc-chip-del { color: #ff4d4f; cursor: pointer; font-size: 13px; line-height: 1; }
.doc-none { color: #ff4d4f; font-size: 13px; }
.doc-actions { flex: 0 0 auto; }
.doc-up { color: #1677ff; cursor: pointer; font-size: 13px; }

/* ===== 后勤单据：卡片式拖拽上传 ===== */
.logi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
  padding: 16px;
}
.logi-ok { color: #52c41a; font-size: 15px; }

/* 后勤单据卡片与随附单据保持一致的最小高度，未上传/已上传两态等高对齐 */
.logi-card .att-doc { min-height: 190px; }
.logi-card .att-doc .att-thumb { flex: 1 1 auto; align-items: center; margin-bottom: 12px; }
.logi-card .logi-dragger { flex: 1 1 auto; display: flex; }
.logi-card .logi-dragger :deep(.ant-upload-wrapper),
.logi-card .logi-dragger :deep(.ant-upload.ant-upload-drag) { width: 100%; height: 100%; }

/* 拖拽上传区：紧凑、柔和 */
.logi-dragger :deep(.ant-upload.ant-upload-drag) {
  border: 1.5px dashed #cdd5e3;
  border-radius: 10px;
  background: #fbfcfe;
  transition: border-color 0.2s, background 0.2s;
}
.logi-dragger :deep(.ant-upload.ant-upload-drag:hover) {
  border-color: #1677ff;
  background: #f3f7ff;
}
.logi-dragger :deep(.ant-upload-btn) { padding: 14px 10px; }
.logi-drag-icon { margin: 0 0 6px; font-size: 30px; color: #9fb4dd; line-height: 1; }
.logi-drag-text { margin: 0; font-size: 13px; color: #3b4757; font-weight: 500; }
.logi-drag-hint { margin: 4px 0 0; font-size: 12px; color: rgba(0, 0, 0, 0.4); }

/* 后勤视角：两个区域上下堆叠（覆盖默认横向 flex） */
.doc-row-wrap > .ant-col.logi-stack { flex-direction: column; }
.logi-stack .doc-card { height: auto; }

/* ===== 随附单据：单文件直接展开，缩略图 + 预览 + 下载 ===== */
.att-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
  padding: 16px;
}
.att-doc {
  border: 1px solid #eef0f4;
  border-radius: 12px;
  padding: 14px;
  background: #fff;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
}
.att-doc:hover {
  border-color: #d6e0ff;
  box-shadow: 0 8px 22px -14px rgba(22, 119, 255, 0.35);
  transform: translateY(-1px);
}
.att-doc.done { border-color: #d3eedd; background: linear-gradient(180deg, #f6fcf8 0%, #ffffff 60%); }
.att-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.att-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
  color: #1f2733;
}
.att-thumb {
  display: flex;
  justify-content: center;
  margin-bottom: 10px;
}
.att-thumb-img :deep(img),
.att-thumb-img {
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid #eef0f4;
  cursor: pointer;
}
.att-thumb-file {
  width: 96px;
  height: 96px;
  border-radius: 8px;
  border: 1px solid #eef0f4;
  background: #f7f9fc;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  color: #8a97ad;
  transition: color 0.2s, border-color 0.2s;
}
.att-thumb-file:hover { color: #1677ff; border-color: #d6e0ff; }
.att-file-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
}
.att-file-name {
  flex: 1 1 auto;
  min-width: 0;
  color: #1f2733;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.att-file-name:hover { color: #1677ff; text-decoration: underline; }
.att-dl { flex: 0 0 auto; color: #1677ff; font-size: 13px; }
.att-dl:hover { text-decoration: underline; }
.att-del { flex: 0 0 auto; color: #bfbfbf; cursor: pointer; font-size: 14px; transition: color 0.15s; }
.att-del:hover { color: #ff4d4f; }
.att-empty { color: #ff4d4f; font-size: 13px; text-align: center; padding: 18px 0; }

/* 压缩空状态：缩小插画、收紧上下间距（含子组件评价记录） */
:deep(.ant-empty-normal) { margin: 12px 0; }
:deep(.ant-empty-normal .ant-empty-image) { height: 32px; }
:deep(.ant-empty-normal .ant-empty-description) { font-size: 12px; color: rgba(0, 0, 0, 0.4); }
</style>
