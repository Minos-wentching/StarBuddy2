<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" class="text-center">
        <div class="text-h1 font-weight-bold text-primary mb-4">404</div>
        <div class="text-h5 text-medium-emphasis mb-6">页面未找到</div>
        <p class="text-body-1 text-disabled mb-8">你访问的页面不存在或已被移除</p>
        <v-btn color="primary" size="large" to="/">
          <v-icon left>mdi-home</v-icon>
          返回首页
        </v-btn>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
</script>
