<template>
  <div
    class="d-flex flex-column align-center justify-center"
    style="min-height: 80vh"
  >
    <v-icon size="120" color="grey lighten-1" class="mb-4">
      mdi-alert-circle-outline
    </v-icon>

    <h1 class="text-h2 mb-2">404</h1>
    <h2 class="text-h4 mb-4 grey--text">Page Not Found</h2>

    <p class="text-subtitle-1 text-center mb-6 grey--text">
      The page you're looking for doesn't exist or has been moved.
    </p>

    <div class="d-flex gap-4">
      <v-btn color="primary" large @click="$router.push('/')">
        <v-icon left>mdi-home</v-icon>
        Go Home
      </v-btn>

      <v-btn color="secondary" large outlined @click="$router.go(-1)">
        <v-icon left>mdi-arrow-left</v-icon>
        Go Back
      </v-btn>
    </div>
  </div>
</template>

<script>
export default {
  name: "NotFound",
};
</script>

<style scoped>
.gap-4 {
  gap: 1rem;
}
</style>
