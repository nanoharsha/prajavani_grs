<template>
  <header class="bg-white border-b border-gray-200 sticky top-0 z-10">
    <div class="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
      <RouterLink to="/" class="flex items-center gap-2 font-bold text-gray-900 text-lg">
        <span class="text-2xl">🏛</span>
        <span>Prajavani <span class="text-brand-500">GRS</span></span>
      </RouterLink>
      <nav class="flex items-center gap-2">
        <RouterLink to="/track"
          class="text-sm font-medium text-gray-600 hover:text-brand-500 px-3 py-1.5 rounded-lg hover:bg-brand-50 transition-colors">
          Track Complaint
        </RouterLink>
        <RouterLink to="/register" class="btn-primary text-sm py-1.5 px-4">
          File Complaint
        </RouterLink>
      </nav>
    </div>
  </header>
</template>
