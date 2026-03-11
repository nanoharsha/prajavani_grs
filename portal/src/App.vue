<template>
  <div class="min-h-screen flex flex-col">
    <NavBar />
    <main class="flex-1">
      <RouterView />
    </main>
    <footer class="border-t border-gray-200 bg-white mt-12">
      <div class="max-w-4xl mx-auto px-4 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-gray-500">
        <span>© {{ new Date().getFullYear() }} Prajavani GRS · Government of Telangana</span>
        <span>Helpline: <a href="tel:1800123456" class="text-brand-500 font-medium">1800-XXX-XXXX</a></span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import NavBar from './components/NavBar.vue'
</script>
