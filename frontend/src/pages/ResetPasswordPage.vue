<template>

<h2>Новый пароль</h2>

<form @submit.prevent="changePassword">

    <input
        v-model="password"
        type="password"
        placeholder="Новый пароль"
    >

    <input
        v-model="password2"
        type="password"
        placeholder="Повторите пароль"
    >

    <button>
        Сохранить
    </button>

</form>

<p>{{ message }}</p>

</template>

<script setup lang="ts">

import { ref } from "vue";
import { useRoute } from "vue-router";

import { resetPassword } from "@/api/auth";

const route = useRoute();

const password = ref("");

const password2 = ref("");

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

    } catch (error: any) {

        message.value =
            error.response?.data?.detail ??
            "Ошибка.";

    }

}

</script>