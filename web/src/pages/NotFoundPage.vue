<script setup lang="ts">
import { Compass } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
</script>

<template>
  <EmptyState :icon="Compass" title="That page does not exist" description="The link may be old, or the page moved. Everything lives in the menu.">
    <Button variant="primary" to="/">Back to the dashboard</Button>
    <Button variant="ghost" to="/miners">See my miners</Button>
  </EmptyState>
</template>
