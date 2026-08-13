<template>
  <div class="auth-card text-center">
    <h2>Подтверждение Email</h2>
    <p v-if="message" class="auth-message static">{{ message }}</p>
  </div>
</template>




<script setup lang="ts">

import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { verifyEmail } from "@/api/auth";

const route = useRoute();

const message = ref("Проверяем ссылку...");

onMounted(async () => {

    const token = route.query.token as string;

    if (!token) {

        message.value = "Токен отсутствует.";

        return;

    }

    try {

        const response = await verifyEmail(token);

        message.value = response.message;

    } catch (error: any) {

        message.value =
            error.response?.data?.detail ??
            "Не удалось подтвердить Email.";

    }

});

</script>



<style scoped>
.auth-card {
  max-width: 400px;
  margin: 60px auto;
  padding: 32px 28px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border: 1px solid #eaeaea;
}

.text-center {
  text-align: center;
}

h2 {
  margin-top: 0;
  margin-bottom: 24px;
  font-size: 22px;
  text-align: center;
  color: #2c3e50;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
}

.auth-input {
  width: 100%;
  box-sizing: border-box;
  padding: 11px 14px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.auth-input:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.15);
}

.auth-btn {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 8px;
  background-color: #1976d2;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
  margin-top: 4px;
}

.auth-btn:hover:not(:disabled) {
  background-color: #1565c0;
}

.auth-btn:disabled {
  background-color: #90caf9;
  cursor: not-allowed;
}

.auth-link-btn {
  background: none;
  border: none;
  color: #1976d2;
  font-size: 13px;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
  margin-top: 8px;
}

.auth-message {
  margin-top: 16px;
  font-size: 14px;
  text-align: center;
  color: #d32f2f;
}

.auth-message.static {
  color: #333;
}
</style>