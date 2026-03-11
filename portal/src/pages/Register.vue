<template>
  <div class="max-w-xl mx-auto px-4 py-10">
    <div class="text-center mb-8">
      <h1 class="text-2xl font-bold text-gray-900">File a Complaint</h1>
      <p class="text-sm text-gray-500 mt-1">Fill in the details below. All fields marked * are required.</p>
    </div>

    <!-- Step indicator -->
    <div class="flex items-center justify-center gap-2 mb-8">
      <div v-for="(s, i) in steps" :key="i" class="flex items-center gap-2">
        <div :class="[
          'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all',
          step > i  ? 'bg-green-500 border-green-500 text-white' :
          step === i ? 'bg-brand-500 border-brand-500 text-white' :
                       'bg-white border-gray-300 text-gray-400'
        ]">
          <span v-if="step > i">✓</span>
          <span v-else>{{ i + 1 }}</span>
        </div>
        <span v-if="i < steps.length - 1" class="h-0.5 w-8 bg-gray-200"></span>
      </div>
    </div>
    <p class="text-center text-sm font-medium text-gray-600 mb-6">{{ steps[step] }}</p>

    <div class="card p-6">

      <!-- Step 0: Personal Details -->
      <div v-if="step === 0" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
          <input v-model="form.name" class="input" placeholder="Your full name" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Mobile Number *</label>
          <input v-model="form.mobile" class="input" placeholder="10-digit mobile number" maxlength="10" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">District *</label>
          <select v-model="form.district" class="input">
            <option value="">Select your district</option>
            <option v-for="d in districts" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>
      </div>

      <!-- Step 1: Complaint Details -->
      <div v-else-if="step === 1" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Department *</label>
          <select v-model="form.department" class="input" @change="loadCategories">
            <option value="">Select department</option>
            <option v-for="d in departments" :key="d.name" :value="d.name">{{ d.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Category *</label>
          <select v-model="form.category" class="input" :disabled="!form.department">
            <option value="">{{ form.department ? 'Select category' : 'Select a department first' }}</option>
            <option v-for="c in categories" :key="c.name" :value="c.name">{{ c.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Describe Your Complaint *</label>
          <textarea v-model="form.gist" class="input resize-none" rows="5"
            placeholder="Please describe your complaint clearly. Include dates, locations, and any relevant details." />
          <p class="text-xs text-gray-400 mt-1">{{ form.gist.length }}/1000 characters</p>
        </div>
      </div>

      <!-- Step 2: Review & Submit -->
      <div v-else-if="step === 2" class="space-y-3">
        <h3 class="font-semibold text-gray-800 mb-4">Please review your complaint before submitting</h3>
        <div class="space-y-2 text-sm">
          <div class="flex gap-3 py-2 border-b border-gray-100">
            <span class="text-gray-400 w-32 flex-shrink-0">Name</span>
            <span class="font-medium text-gray-800">{{ form.name }}</span>
          </div>
          <div class="flex gap-3 py-2 border-b border-gray-100">
            <span class="text-gray-400 w-32 flex-shrink-0">Mobile</span>
            <span class="font-medium text-gray-800">{{ form.mobile }}</span>
          </div>
          <div class="flex gap-3 py-2 border-b border-gray-100">
            <span class="text-gray-400 w-32 flex-shrink-0">District</span>
            <span class="font-medium text-gray-800">{{ form.district }}</span>
          </div>
          <div class="flex gap-3 py-2 border-b border-gray-100">
            <span class="text-gray-400 w-32 flex-shrink-0">Department</span>
            <span class="font-medium text-gray-800">{{ form.department }}</span>
          </div>
          <div class="flex gap-3 py-2 border-b border-gray-100">
            <span class="text-gray-400 w-32 flex-shrink-0">Category</span>
            <span class="font-medium text-gray-800">{{ form.category }}</span>
          </div>
          <div class="flex gap-3 py-2">
            <span class="text-gray-400 w-32 flex-shrink-0">Complaint</span>
            <span class="text-gray-800">{{ form.gist }}</span>
          </div>
        </div>
        <div v-if="submitError" class="text-red-600 text-sm bg-red-50 rounded-lg p-3">{{ submitError }}</div>
      </div>

      <!-- Success -->
      <div v-else class="text-center py-4">
        <div class="text-5xl mb-4">✅</div>
        <h3 class="text-lg font-bold text-gray-900 mb-1">Complaint Filed Successfully!</h3>
        <p class="text-sm text-gray-500 mb-4">Your registration number is:</p>
        <div class="bg-gray-50 rounded-lg px-5 py-3 font-mono text-brand-600 font-bold text-lg mb-6">
          {{ submittedReg }}
        </div>
        <p class="text-xs text-gray-400 mb-6">Save this number to track your complaint status.</p>
        <RouterLink :to="`/track?reg=${submittedReg}`" class="btn-primary">Track My Complaint →</RouterLink>
      </div>

    </div>

    <!-- Navigation buttons -->
    <div v-if="step < 3" class="flex justify-between mt-5">
      <button v-if="step > 0" class="btn-secondary" @click="step--">← Back</button>
      <div v-else></div>
      <button v-if="step < 2" class="btn-primary" :disabled="!canProceed" @click="step++">
        Next →
      </button>
      <button v-else class="btn-primary" :disabled="submitting" @click="submit">
        <span v-if="submitting">Submitting…</span>
        <span v-else>Submit Complaint</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api/index.js'

const steps = ['Personal Details', 'Complaint Details', 'Review & Submit']
const step  = ref(0)

const districts = [
  'Adilabad', 'Bhadradri Kothagudem', 'Hyderabad', 'Jagtial', 'Jangaon',
  'Jayashankar Bhupalpally', 'Jogulamba Gadwal', 'Kamareddy', 'Karimnagar',
  'Khammam', 'Komaram Bheem', 'Mahabubabad', 'Mahabubnagar', 'Mancherial',
  'Medak', 'Medchal–Malkajgiri', 'Mulugu', 'Nagarkurnool', 'Nalgonda',
  'Narayanpet', 'Nirmal', 'Nizamabad', 'Peddapalli', 'Rajanna Sircilla',
  'Rangareddy', 'Sangareddy', 'Siddipet', 'Suryapet', 'Vikarabad',
  'Wanaparthy', 'Warangal Rural', 'Warangal Urban', 'Yadadri Bhuvanagiri',
]

const departments  = ref([])
const categories   = ref([])
const submitting   = ref(false)
const submitError  = ref('')
const submittedReg = ref('')

const form = ref({ name: '', mobile: '', district: '', department: '', category: '', gist: '' })

onMounted(async () => {
  try { departments.value = await api.getDepartments() } catch {}
})

async function loadCategories() {
  form.value.category = ''
  try { categories.value = await api.getCategories(form.value.department) } catch {}
}

const canProceed = computed(() => {
  if (step.value === 0) return form.value.name && form.value.mobile.length === 10 && form.value.district
  if (step.value === 1) return form.value.department && form.value.category && form.value.gist.length >= 20
  return true
})

async function submit() {
  submitting.value = true
  submitError.value = ''
  try {
    // Citizens file via Frappe desk login for now; this is a placeholder.
    // Full guest filing requires OTP verification (future sprint).
    await new Promise(r => setTimeout(r, 1200))
    submittedReg.value = 'GRS/' + new Date().getFullYear() + '/DEMO/00001'
    step.value = 3
  } catch (e) {
    submitError.value = 'Submission failed. Please try again or call the helpline.'
  } finally {
    submitting.value = false
  }
}
</script>
