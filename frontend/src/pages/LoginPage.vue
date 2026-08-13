<template>
  <div class="auth-card">
    <h2>Вход</h2>

    <form class="auth-form" @submit.prevent="loginUser">
      <div class="field">
        <input
          v-model="loginValue"
          type="text"
          class="auth-input"
          placeholder="Username или Email"
          required
        >
      </div>

      <div class="field">
        <input
          v-model="password"
          type="password"
          class="auth-input"
          placeholder="Password"
          required
        >
      </div>

      <button
        type="submit"
        class="auth-btn btn-primary"
        :disabled="loading || retryAfter > 0"
      >
        {{
          retryAfter > 0
            ? `Повторить через ${retryAfter} сек.`
            : loading
              ? "Подождите..."
              : "Войти"
        }}
      </button>

      <button
        type="button"
        class="auth-link-btn"
        @click="router.push('/forgot-password')"
      >
        Забыли пароль?
      </button>
    </form>

    <p v-if="message" class="auth-message">{{ message }}</p>
  </div>
</template>





<script setup lang="ts">

import { ref } from "vue";
import { useRouter } from "vue-router";

import { login } from "@/api/auth";
import { useAuthStore } from "@/stores/auth";
import { getCurrentUser } from "@/api/auth";

import { onUnmounted } from "vue";

const router = useRouter();

const auth = useAuthStore();

const loginValue = ref("");

const password = ref("");

const message = ref("");

const loading = ref(false);

const retryAfter = ref(0);

let timer: number | null = null;


function startRetryTimer(seconds: number) {

    retryAfter.value = seconds;

    if (timer !== null) {
        clearInterval(timer);
    }

    timer = window.setInterval(() => {

        retryAfter.value--;

        if (retryAfter.value <= 0) {

            clearInterval(timer!);

            timer = null;

        }

    }, 1000);

}

function validate(): string | null {


    if (!loginValue.value.trim()) {
        return "Введите имя пользователя или Email";
    }

    if (!password.value) {
        return "Введите пароль";
    }

    if (password.value.length < 8 || password.value.length > 50) {
        return "Пароль должен содержать от 8 до 50 символов";
    }

    return null;
}

async function loginUser() {

    loading.value = true;

    message.value = "";
    const error = validate();
    if (error) {
        message.value = error;
        loading.value = false;
        return;
    }

    try {

        const tokens = await login({
            login: loginValue.value,
            password: password.value,
        });

        auth.setAccessToken(tokens.access_token);

        const user = await getCurrentUser();
        auth.setUser(user);

        router.push("/");

    } catch (error: any) {

        loading.value = false;

        if (error.response?.status === 401) {

            message.value = "Неверное имя пользователя или пароль";

        } else if (error.response?.status === 429) {

            const seconds = error.response.data.detail.retry_after;

            startRetryTimer(seconds);

            message.value =
                error.response.data.detail.message;

        } else {

            message.value = "Не удалось выполнить вход";

        }

    }

}

onUnmounted(() => {

    if (timer !== null) {
        clearInterval(timer);
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