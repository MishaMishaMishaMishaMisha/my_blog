<template>

<h2>Регистрация</h2>

<form @submit.prevent="registerUser">

    <input
        v-model="username"
        placeholder="Username"
    >

    <input
        v-model="email"
        type="email"
        placeholder="Email"
    >

    <input
        v-model="password"
        type="password"
        placeholder="Password"
    >

    <button :disabled="loading">
        {{ loading ? "Подождите..." : "Зарегистрироваться" }}
    </button>

</form>

<p>{{ message }}</p>

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

        message.value = error.response.data.detail.message;

        loading.value = false

    }

}

</script>