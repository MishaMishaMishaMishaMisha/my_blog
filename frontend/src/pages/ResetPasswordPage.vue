<template>
  <div class="auth-card">
    <h2>Новый пароль</h2>

    <!-- Форма отображается только если пароль еще не изменен -->
    <form v-if="!isSuccess" class="auth-form" @submit.prevent="changePassword">
      <div class="field">
        <input
          v-model="password"
          type="password"
          class="auth-input"
          placeholder="Новый пароль"
          required
        >
      </div>

      <div class="field">
        <input
          v-model="password2"
          type="password"
          class="auth-input"
          placeholder="Повторите пароль"
          required
        >
      </div>

      <button type="submit" class="auth-btn btn-primary">
        Сохранить
      </button>
    </form>

    <!-- Сообщение от сервера -->
    <p v-if="message" :class="['auth-message', { 'success': isSuccess }]">{{ message }}</p>

    <!-- Кнопка входа появляется после успешной смены пароля -->
    <button v-if="isSuccess" class="auth-btn btn-primary login-redirect-btn" @click="goToLogin">
      Войти в аккаунт
    </button>
  </div>
</template>



<script setup lang="ts">

import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { resetPassword } from "@/api/auth";

const route = useRoute();

const router = useRouter();

const password = ref("");

const password2 = ref("");

const isSuccess = ref(false);

const message = ref("");

async function changePassword() {

    if (password.value.length < 8 || password.value.length > 50) {

        message.value =
            "Пароль должен содержать от 8 до 50 символов.";

        return;

    }

    if (password.value !== password2.value) {

        message.value = "Пароли не совпадают.";

        return;

    }

    try {

        const token = route.query.token as string;

        const response =
            await resetPassword(
                token,
                password.value,
            );

        message.value = response.message;
        isSuccess.value = true;

    } catch (error: any) {

        message.value =
            error.response?.data?.detail ??
            "Ошибка.";
        
        isSuccess.value = false; 

    }

}

function goToLogin() {
    router.push("/login");
}
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

.login-redirect-btn {
  margin-top: 16px; /* Небольшой отступ от сообщения об успехе */
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

/* Зеленый цвет для успешного сообщения */
.auth-message.success {
  color: #2e7d32;
}

.auth-message.static {
  color: #333;
}
</style>