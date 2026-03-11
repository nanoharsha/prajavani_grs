<template>
  <div>
    <!-- Hero -->
    <section class="bg-gradient-to-br from-brand-600 to-brand-700 text-white">
      <div class="max-w-4xl mx-auto px-4 py-16 text-center">
        <h1 class="text-3xl sm:text-4xl font-bold mb-3 leading-tight">
          Your Complaint, Our Responsibility
        </h1>
        <p class="text-brand-100 text-lg mb-10">
          File grievances with the government and track their resolution — simply and transparently.
        </p>

        <!-- Search box -->
        <div class="bg-white rounded-xl p-4 sm:p-5 max-w-xl mx-auto shadow-lg">
          <p class="text-sm font-medium text-gray-600 mb-2 text-left">Already filed a complaint? Track it here</p>
          <div class="flex gap-2">
            <input
              v-model="regNo"
              type="text"
              placeholder="e.g. GRS/2026/ADI/00001"
              class="input text-gray-800 flex-1"
              @keyup.enter="doTrack"
            />
            <button class="btn-primary whitespace-nowrap" :disabled="!regNo.trim()" @click="doTrack">
              Track →
            </button>
          </div>
          <p v-if="error" class="text-red-500 text-xs mt-2">{{ error }}</p>
        </div>
      </div>
    </section>

    <!-- Action cards -->
    <section class="max-w-4xl mx-auto px-4 py-12">
      <div class="grid sm:grid-cols-3 gap-5">
        <RouterLink to="/register" class="card p-6 hover:shadow-md hover:border-brand-300 transition-all group cursor-pointer block">
          <div class="text-3xl mb-3">📋</div>
          <h3 class="font-semibold text-gray-900 mb-1 group-hover:text-brand-600">File a Complaint</h3>
          <p class="text-sm text-gray-500">Submit a new grievance to the appropriate department.</p>
        </RouterLink>

        <RouterLink to="/track" class="card p-6 hover:shadow-md hover:border-brand-300 transition-all group cursor-pointer block">
          <div class="text-3xl mb-3">🔍</div>
          <h3 class="font-semibold text-gray-900 mb-1 group-hover:text-brand-600">Track Status</h3>
          <p class="text-sm text-gray-500">Check the current status and history of your complaint.</p>
        </RouterLink>

        <div class="card p-6">
          <div class="text-3xl mb-3">📞</div>
          <h3 class="font-semibold text-gray-900 mb-1">Need Help?</h3>
          <p class="text-sm text-gray-500 mb-2">Call our citizen helpline, available Mon–Sat, 9am–6pm.</p>
          <a href="tel:1800123456" class="text-brand-500 font-semibold text-sm">1800-XXX-XXXX</a>
        </div>
      </div>
    </section>

    <!-- How it works -->
    <section class="bg-white border-t border-gray-100 py-12">
      <div class="max-w-4xl mx-auto px-4">
        <h2 class="text-xl font-bold text-gray-900 text-center mb-8">How It Works</h2>
        <div class="grid sm:grid-cols-4 gap-6">
          <div v-for="(step, i) in howItWorks" :key="i" class="text-center">
            <div class="w-12 h-12 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center text-xl font-bold mx-auto mb-3">
              {{ i + 1 }}
            </div>
            <h4 class="font-semibold text-gray-800 text-sm mb-1">{{ step.title }}</h4>
            <p class="text-xs text-gray-500">{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const regNo  = ref('')
const error  = ref('')

const howItWorks = [
  { title: 'File Complaint',    desc: 'Submit your grievance online or at your nearest desk.' },
  { title: 'Officer Assigned',  desc: 'An officer from the relevant department is assigned within 48 hours.' },
  { title: 'Investigation',     desc: 'The officer investigates and may contact you for details.' },
  { title: 'Resolution',        desc: 'You receive a formal response. If unsatisfied, you can appeal.' },
]

function doTrack() {
  const reg = regNo.value.trim()
  if (!reg) { error.value = 'Please enter a registration number.'; return }
  router.push({ path: '/track', query: { reg } })
}
</script>
