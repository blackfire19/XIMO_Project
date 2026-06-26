<template>
  <div class="board">
    <!-- 底层：世界地图背景 -->
    <div ref="chartRef" class="board-chart"></div>

    <!-- 极细微哑光金属颗粒肌理（钢铁工业质感，不遮挡交互） -->
    <div class="board-grain"></div>

    <!-- 悬浮层：顶部品牌 + 数据卡 -->
    <div class="board-overlay">
      <!-- 左上品牌标题区 -->
      <div class="brand">
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
        <div class="brand-text">
          <div class="brand-title">西莫金属·全球业务大屏</div>
          <div class="brand-sub">XIMOSTEEL 跨境钢铁贸易可视化中枢</div>
        </div>
      </div>

      <!-- 右上核心数据区（三栏磨砂黑金卡） -->
      <div class="stat-cards">
        <div class="stat-card">
          <div class="stat-label">进行中订单航线</div>
          <div class="stat-value"><b>{{ totalOrders }}</b> 单 · {{ routeCountryCount }} 国</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">海外客户覆盖</div>
          <div class="stat-value"><b>{{ customerCountryCount }}</b> 国</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">数据更新时间</div>
          <div class="stat-time">{{ updatedAt || '加载中…' }}</div>
        </div>
      </div>
    </div>

    <!-- 图例 -->
    <div class="board-legend">
      <span class="legend-label">客户数量</span>
      <span class="legend-min">少</span>
      <span class="legend-bar"></span>
      <span class="legend-max">多</span>
      <span class="legend-route"><i class="dot"></i>出运目的国</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import worldJson from '@/assets/world.json'
import { dashboardApi } from '@/api/dashboard'

echarts.registerMap('world', worldJson)

// 我们库里存的英文名 → GeoJSON 中的名字（仅这 4 个不一致）
const NAME_MAP = {
  'Czech Republic': 'Czech Rep.',
  'South Korea': 'Korea',
  'Dominican Republic': 'Dominican Rep.',
  'DR Congo': 'Dem. Rep. Congo',
}
const toGeoName = (n) => NAME_MAP[n] || n

// 起点：上海（沿海，航线扇形展开更自然）
const ORIGIN = [121.47, 31.23]

// 从 GeoJSON 计算每个国家中心点（取顶点最多的那个环求平均，足够画飞线终点）
const CENTROIDS = (() => {
  const map = {}
  for (const f of worldJson.features) {
    const name = f.properties && f.properties.name
    if (!name) continue
    const geom = f.geometry
    if (!geom) continue
    const polygons = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates
    let best = null
    for (const poly of polygons) {
      const ring = poly[0]
      if (!ring) continue
      if (!best || ring.length > best.length) best = ring
    }
    if (!best) continue
    let sx = 0, sy = 0
    for (const [x, y] of best) { sx += x; sy += y }
    map[name] = [sx / best.length, sy / best.length]
  }
  return map
})()

const chartRef = ref(null)
let chart = null
let timer = null

const totalOrders = ref(0)
const routeCountryCount = ref(0)
const customerCountryCount = ref(0)
const updatedAt = ref('')

// 品牌 LOGO（复用登录页）
const showLogo = ref(true)
const logoSrc = '/logo.jpg'

function fmtNow() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

// 客户数 → 香槟金渐变：暗古铜（客户少）→ 浅香槟（客户多）
function heatColor(ratio) {
  const from = [74, 55, 24]    // #4A3718 暗古铜
  const to = [234, 208, 143]   // #EAD08F 浅香槟
  const c = from.map((f, i) => Math.round(f + (to[i] - f) * ratio))
  return `rgb(${c[0]},${c[1]},${c[2]})`
}

function buildOption(data) {
  const customers = data.customers || []
  const routes = data.routes || []

  // 热力：按客户数给国家区域上色（手动 geo.regions，避免与 lines 的 map 系列冲突）
  const maxCust = Math.max(1, ...customers.map((c) => c.count))
  const regions = customers.map((c) => ({
    name: toGeoName(c.country),
    itemStyle: { areaColor: heatColor(c.count / maxCust) },
  }))

  // 航线 + 终点光点
  const lineData = []
  const scatterData = []
  for (const r of routes) {
    const dest = CENTROIDS[toGeoName(r.country)]
    if (!dest) continue
    lineData.push({ coords: [ORIGIN, dest], value: r.order_count })
    scatterData.push({ name: r.country, value: [...dest, r.order_count] })
  }

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(20,16,9,0.92)',
      borderColor: '#D4AF37',
      textStyle: { color: '#F8F3E8' },
    },
    geo: {
      map: 'world',
      roam: false,
      zoom: 1.2,
      itemStyle: {
        areaColor: 'rgba(58, 46, 26, 0.16)',     // 无业务陆地：极低透明度暗古铜，弱化存在感
        borderColor: 'rgba(176, 141, 87, 0.32)', // 细古铜浅线勾勒轮廓
        borderWidth: 0.5,
      },
      emphasis: { disabled: true },
      regions,
      silent: false,
    },
    series: [
      {
        name: '出运航线',
        type: 'lines',
        coordinateSystem: 'geo',
        zlevel: 2,
        effect: {
          show: true,
          period: 9,                          // 缓慢流动
          trailLength: 0.65,                  // 长柔拖尾，低调动态
          symbol: 'circle',
          symbolSize: 3,
          color: 'rgba(234, 208, 143, 0.9)',  // 微弱鎏金流光
        },
        lineStyle: {
          color: '#C9A86A',
          width: 1,
          opacity: 0.12,                      // 底线近乎隐形，取消生硬实线
          curveness: 0.25,
        },
        data: lineData,
      },
      {
        // 目的国节点：双层柔光古铜金（静态柔光，禁止强光闪烁）
        name: '目的国',
        type: 'scatter',
        coordinateSystem: 'geo',
        zlevel: 3,
        symbolSize: (val) => Math.min(20, 8 + val[2] * 2),
        itemStyle: {
          color: '#D4AF37',                        // 内核古铜金
          borderColor: 'rgba(248,243,232,0.45)',   // 外圈微米白
          borderWidth: 1,
          shadowColor: 'rgba(212,175,55,0.4)',     // 低强度暖金柔光
          shadowBlur: 10,
        },
        tooltip: {
          formatter: (p) => `${p.name}：进行中订单 ${p.value[2]} 单`,
        },
        data: scatterData,
      },
    ],
  }
}

async function loadData() {
  try {
    const res = await dashboardApi.worldMap()
    const data = res.data
    totalOrders.value = (data.routes || []).reduce((s, r) => s + r.order_count, 0)
    routeCountryCount.value = (data.routes || []).length
    customerCountryCount.value = (data.customers || []).length
    chart && chart.setOption(buildOption(data), true)
    updatedAt.value = fmtNow()
  } catch (e) {
    // 大屏无人值守，静默失败，下个周期重试
  }
}

function onResize() {
  chart && chart.resize()
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  loadData()
  timer = setInterval(loadData, 60000)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('resize', onResize)
  chart && chart.dispose()
  chart = null
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');

.board {
  position: fixed;
  inset: 0;
  font-family: 'Noto Sans SC', -apple-system, 'Microsoft YaHei', sans-serif;
  /* 暖棕径向渐变深底：中心深炭褐黑 → 边缘暗古铜，叠顶部暖金光晕 + 拉丝纹理 */
  background:
    repeating-linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.014) 0 1px,
      transparent 1px 20px
    ),
    radial-gradient(95% 55% at 50% 0%, rgba(150, 112, 52, 0.22), transparent 62%),
    radial-gradient(ellipse at 50% 46%, #0c0a06 0%, #15100a 56%, #241a0d 100%);
  overflow: hidden;
}

/* 二级：世界地图——四周内缩留出渐变暗留白，不全屏铺满，作为背景画框中的主体 */
.board-chart {
  position: absolute;
  top: 104px;
  right: 56px;
  bottom: 92px;
  left: 56px;
  z-index: 1;
}

/* 悬浮层：顶部品牌 + 数据卡 */
.board-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 28px 36px;
  pointer-events: none;  /* 悬浮层不遮挡地图交互 */
  /* 顶部暗角下压，强化景深、托起卡片 */
  background: linear-gradient(180deg, rgba(8, 6, 3, 0.55) 0%, rgba(8, 6, 3, 0) 100%);
}

/* 左上品牌标题区 */
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
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
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
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
  color: #D4AF37;
}
/* 一级：品牌大标题——衬线鎏金粗体，与登录页同字族同字重，字号放大领衔 */
.brand-title {
  font-family: 'Noto Serif SC', 'Songti SC', STSong, serif;
  font-size: 34px;
  font-weight: 700;
  color: #D4AF37;
  letter-spacing: 3px;
  line-height: 1.2;
  text-shadow: 0 0 18px rgba(212, 175, 55, 0.25);
}
/* 辅助说明：无衬线细体浅香槟，缩小降权 */
.brand-sub {
  margin-top: 7px;
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 12.5px;
  font-weight: 400;
  letter-spacing: 1.5px;
  color: rgba(226, 202, 144, 0.7);  /* 浅香槟 */
}

/* 右上核心数据区：三栏磨砂黑金半透卡 */
.stat-cards {
  display: flex;
  gap: 16px;
  pointer-events: auto;
}
.stat-card {
  min-width: 150px;
  padding: 12px 20px;
  border-radius: 8px;  /* 与登录框圆角一致 */
  background: rgba(20, 16, 9, 0.55);
  border: 1px solid rgba(212, 175, 55, 0.22);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  /* 外投影托起景深 + 极细微内阴影勾勒磨砂玻璃边缘 */
  box-shadow:
    0 10px 28px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(248, 243, 232, 0.06),
    inset 0 0 0 1px rgba(0, 0, 0, 0.18);
}
/* 辅助说明：无衬线细体浅香槟，缩小降权 */
.stat-label {
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 12.5px;
  font-weight: 400;
  letter-spacing: 1.2px;
  color: rgba(248, 243, 232, 0.55);
  margin-bottom: 7px;
}
/* 一级：核心经营数值——衬线鎏金加粗超大字号，视觉权重与登录页 38/12/99.2 统一 */
.stat-value {
  font-size: 14px;
  color: rgba(248, 243, 232, 0.78);
  display: flex;
  align-items: baseline;
}
.stat-value b {
  font-family: 'Noto Serif SC', serif;
  font-size: 38px;
  font-weight: 700;
  color: #D4AF37;
  margin-right: 6px;
  line-height: 1;
}
.stat-time {
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 15px;
  font-weight: 400;
  color: rgba(248, 243, 232, 0.55);
  font-variant-numeric: tabular-nums;
}

/* 图例：半透黑金磨砂圆角小卡，统一容器肌理 */
.board-legend {
  position: absolute;
  left: 36px;
  bottom: 28px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 9px 18px;
  border-radius: 8px;
  background: rgba(20, 16, 9, 0.55);
  border: 1px solid rgba(212, 175, 55, 0.22);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow:
    0 10px 28px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(248, 243, 232, 0.06),
    inset 0 0 0 1px rgba(0, 0, 0, 0.18);
  color: rgba(248, 243, 232, 0.78);
  font-size: 12.5px;
  font-weight: 300;
  letter-spacing: 0.5px;
}
.legend-label {
  color: rgba(248, 243, 232, 0.78);
}
.legend-min,
.legend-max {
  color: rgba(248, 243, 232, 0.45);
}
.legend-bar {
  width: 150px;
  height: 9px;
  border-radius: 5px;
  background: linear-gradient(90deg, #4A3718, #EAD08F);
}
.legend-route {
  margin-left: 22px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: rgba(248, 243, 232, 0.7);
}
/* 出运目的国：哑光鎏金小圆，与地图节点视觉统一（低强度暖金柔光） */
.legend-route .dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #D4AF37;
  border: 1px solid rgba(248, 243, 232, 0.45);
  box-shadow: 0 0 5px rgba(212, 175, 55, 0.45);
}

/* 极细微哑光金属颗粒肌理：SVG fractalNoise，超低不透明度，不夺视线、不遮交互 */
.board-grain {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  opacity: 0.05;
  mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size: 160px 160px;
}
</style>
