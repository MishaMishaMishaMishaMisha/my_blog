<template>

<h2>Вход</h2>

<form @submit.prevent="loginUser">

    <input
        v-model="loginValue"
        placeholder="Username или Email"
    >

    <input
        v-model="password"
        type="password"
        placeholder="Password"
    >

    <button
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

    <br><br>

    <button
        type="button"
        @click="router.push('/forgot-password')"
    >
        Забыли пароль?
    </button>

    </form>

<p>{{ message }}</p>

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