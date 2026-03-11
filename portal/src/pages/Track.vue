<template>
  <div class="max-w-2xl mx-auto px-4 py-8">

    <!-- Search bar -->
    <div class="card p-4 mb-6 flex gap-2">
      <input v-model="regNo" type="text" placeholder="Enter Registration Number" class="input flex-1" @keyup.enter="load" />
      <button class="btn-primary" :disabled="loading || !regNo.trim()" @click="load">
        <span v-if="loading">…</span>
        <span v-else>Track</span>
      </button>
    </div>

    <!-- Error -->
    <div v-if="error" class="card p-5 text-center text-red-600">
      <div class="text-3xl mb-2">🔍</div>
      <p class="font-medium">{{ error }}</p>
      <p class="text-sm text-gray-500 mt-1">Check your registration number and try again.</p>
    </div>

    <!-- Result -->
    <template v-else-if="data">

      <!-- Status header -->
      <div class="card p-5 mb-5">
        <div class="flex flex-wrap items-start justify-between gap-3 mb-3">
          <div>
            <p class="text-xs text-gray-400 font-mono mb-0.5">{{ data.registration_no }}</p>
            <h2 class="text-lg font-bold text-gray-900">{{ data.department }} — {{ data.category }}</h2>
            <p class="text-sm text-gray-500 mt-0.5">Filed {{ daysAgo(data.filing_date) }}</p>
          </div>
          <span :class="statusBadgeClass">{{ data.status_label }}</span>
        </div>
        <p class="text-sm text-gray-600 bg-gray-50 rounded-lg px-4 py-3 leading-relaxed">{{ data.status_desc }}</p>
        <p v-if="data.officer_name" class="text-sm text-gray-500 mt-3">
          Officer handling your complaint: <strong class="text-gray-800">{{ data.officer_name }}</strong>
        </p>
      </div>

      <!-- Progress stepper -->
      <div class="card p-5 mb-5">
        <h3 class="text-sm font-semibold text-gray-700 mb-5">Complaint Progress</h3>
        <div class="relative">
          <!-- Spine -->
          <div class="absolute left-[18px] top-0 bottom-0 w-0.5 bg-gray-200"></div>

          <div v-for="(step, i) in data.steps" :key="i" class="relative flex items-start gap-4 mb-5 last:mb-0">
            <!-- Dot -->
            <div :class="[
              'w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 z-10 text-sm font-bold border-2',
              step.done    ? 'bg-green-500 border-green-500 text-white' :
              step.active  ? 'bg-brand-500 border-brand-500 text-white animate-pulse' :
                             'bg-white border-gray-300 text-gray-400'
            ]">
              <span v-if="step.done">✓</span>
              <span v-else-if="step.active">⟳</span>
              <span v-else>{{ i + 1 }}</span>
            </div>
            <!-- Label -->
            <div class="pt-1.5">
              <p :class="['font-medium text-sm', step.done ? 'text-gray-900' : step.active ? 'text-brand-600' : 'text-gray-400']">
                {{ step.label }}
              </p>
              <p v-if="step.date" class="text-xs text-gray-400 mt-0.5">{{ fmtDate(step.date) }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Timeline -->
      <div v-if="data.timeline.length" class="card p-5 mb-5">
        <h3 class="text-sm font-semibold text-gray-700 mb-4">What Happened So Far</h3>
        <div v-for="(ev, i) in data.timeline" :key="i" class="mb-4 last:mb-0">
          <button
            class="w-full text-left flex items-center justify-between gap-3 group"
            @click="ev._open = !ev._open"
          >
            <div class="flex items-center gap-3">
              <span :class="['w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0', typeStyle(ev.type).bg]">
                {{ typeStyle(ev.type).icon }}
              </span>
              <div>
                <p class="font-medium text-sm text-gray-900">{{ ev.title }}</p>
                <p class="text-xs text-gray-400">{{ fmtDate(ev.date) }}<span v-if="ev.officer"> · {{ ev.officer }}</span></p>
              </div>
            </div>
            <span class="text-gray-400 text-xs transition-transform duration-200" :class="ev._open ? 'rotate-180' : ''">▼</span>
          </button>

          <!-- Expanded details -->
          <div v-if="ev._open && Object.keys(ev.details || {}).length" class="mt-3 ml-11 bg-gray-50 rounded-lg p-3 space-y-1.5">
            <div v-for="(val, key) in ev.details" :key="key" class="flex gap-2 text-sm">
              <span class="text-gray-400 min-w-[130px] flex-shrink-0">{{ key }}</span>
              <span class="text-gray-800">{{ val }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Gist -->
      <div class="card p-5 mb-5">
        <h3 class="text-sm font-semibold text-gray-700 mb-2">Your Complaint</h3>
        <p class="text-sm text-gray-600 leading-relaxed">{{ data.gist }}</p>
      </div>

      <!-- Appeal CTA -->
      <div v-if="data.can_appeal" class="card p-5 bg-amber-50 border-amber-200 text-center">
        <p class="font-semibold text-amber-900 mb-1">Not satisfied with the resolution?</p>
        <p class="text-sm text-amber-700 mb-4">You can file an appeal to have your case reviewed by a senior authority.</p>
        <RouterLink :to="`/register?appeal=${data.registration_no}`" class="btn-primary bg-amber-600 hover:bg-amber-700 focus:ring-amber-500">
          File an Appeal
        </RouterLink>
      </div>

    </template>

    <!-- Empty state -->
    <div v-else-if="!loading" class="text-center text-gray-400 py-16">
      <div class="text-5xl mb-4">🔍</div>
      <p class="font-medium text-gray-500">Enter your registration number above to track your complaint.</p>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/index.js'

const route  = useRoute()
const regNo  = ref('')
const data   = ref(null)
const error  = ref('')
const loading = ref(false)

onMounted(() => {
  if (route.query.reg) {
    regNo.value = route.query.reg
    load()
  }
})

async function load() {
  const reg = regNo.value.trim()
  if (!reg) return
  loading.value = true
  error.value   = ''
  data.value    = null
  try {
    const res = await api.trackGrievance(reg)
    if (res?.error) { error.value = res.error }
    else {
      // add reactive _open flag to each timeline event
      res.timeline = (res.timeline || []).map(ev => reactive({ ...ev, _open: false }))
      data.value = res
    }
  } catch (e) {
    error.value = 'Could not connect. Please try again.'
  } finally {
    loading.value = false
  }
}

const STATUS_COLORS = {
  'Received':                  'bg-gray-100 text-gray-700',
  'Officer Assigned':          'bg-blue-100 text-blue-700',
  'Under Review':              'bg-blue-100 text-blue-700',
  'Being Investigated':        'bg-indigo-100 text-indigo-700',
  'Update Sent':               'bg-purple-100 text-purple-700',
  'Sub-Judice':                'bg-red-100 text-red-700',
  'Policy Decision Pending':   'bg-orange-100 text-orange-700',
  'Resolved':                  'bg-green-100 text-green-700',
  'Appeal in Progress':        'bg-amber-100 text-amber-700',
}

const statusBadgeClass = computed(() =>
  `text-xs font-semibold px-3 py-1.5 rounded-full ${STATUS_COLORS[data.value?.status_label || ''] || 'bg-gray-100 text-gray-600'}`
)

function typeStyle(type) {
  return {
    atr:    { bg: 'bg-green-100',  icon: '✅' },
    appeal: { bg: 'bg-amber-100',  icon: '⚖️' },
  }[type] || { bg: 'bg-gray-100', icon: '📌' }
}

function fmtDate(d) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch { return d }
}

function daysAgo(d) {
  if (!d) return ''
  const days = Math.floor((Date.now() - new Date(d)) / 86400000)
  if (days === 0) return 'today'
  if (days === 1) return 'yesterday'
  return `${days} days ago`
}
</script>
