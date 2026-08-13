<template>
  <div class="auth-card">
    <h2>Регистрация</h2>

    <form class="auth-form" @submit.prevent="registerUser">
      <div class="field">
        <input
          v-model="username"
          type="text"
          class="auth-input"
          placeholder="Username"
          required
        >
      </div>

      <div class="field">
        <input
          v-model="email"
          type="email"
          class="auth-input"
          placeholder="Email"
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
        :disabled="loading"
      >
        {{ loading ? "Подождите..." : "Зарегистрироваться" }}
      </button>
    </form>

    <p v-if="message" class="auth-message">{{ message }}</p>
  </div>
</template>




<script setup lang="ts">

import { ref } from "vue";
import { useRouter } from "vue-router";
import { getCurrentUser } from "@/api/auth";

import { register, login } from "@/api/auth";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();

const username = ref("");
const email = ref("");
const password = ref("");

const message = ref("");

const loading = ref(false);

function validate(): string | null {

    if (!username.value.trim()) {
        return "Введите имя пользователя";
    }

    if (username.value.length < 5 || username.value.length > 20) {
        return "Имя пользователя должно содержать от 5 до 20 символов";
    }

    if (!email.value.trim()) {
        return "Введите Email";
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(email.value)) {
        return "Некорректный Email";
    }

    if (!password.value) {
        return "Введите пароль";
    }

    if (password.value.length < 8 || password.value.length > 50) {
        return "Пароль должен содержать от 8 до 50 символов";
    }

    return null;
}

async function registerUser() {

    loading.value = true;

    message.value = "";
    const error = validate();
    if (error) {
        message.value = error;
        loading.value = false;
        return;
    }

    try {


        await register({
            username: username.value,
            email: email.value,
            password: password.value,
        });

        const tokens = await login({
            login: username.value,
            password: password.value,
        });

        auth.setAccessToken(tokens.access_token);

        const user = await getCurrentUser();
        auth.setUser(user);

        message.value =
            "Регистрация успешна. Письмо отправлено на вашу почту.";

        router.push("/");

    } catch (error: any) {
        console.error(error); // Полезно для отладки в консоли

        // Проверяем разные возможные структуры ответа от бэкенда
        if (error.response?.data) {
            const data = error.response.data;
            
            // Если бэкенд возвращает объект со строкой в detail (например, FastAPI: { detail: "User already exists" })
            if (typeof data.detail === "string") {
                message.value = data.detail;
            } 
            // Если ваша старая структура с вложенным объектом
            else if (data.detail?.message) {
                message.value = data.detail.message;
            } 
            // Если бэкенд шлет просто сообщение в message
            else if (data.message) {
                message.value = data.message;
            } 
            else {
                message.value = "Произошла ошибка при регистрации";
            }
        } else {
            message.value = "Ошибка соединения с сервером";
        }
    } finally {
        // Обязательно возвращаем кнопке активное состояние в любом случае
        loading.value = false;
    }

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