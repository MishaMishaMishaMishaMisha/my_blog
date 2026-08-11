<template>

<h2>Восстановление пароля</h2>

<form @submit.prevent="send">

    <input
        v-model="email"
        type="email"
        placeholder="Email"
    >

    <button>
        Отправить письмо
    </button>

</form>

<p>{{ message }}</p>

</template>

<script setup lang="ts">

import { ref } from "vue";

import { forgotPassword } from "@/api/auth";

const email = ref("");

const message = ref("");

async function send() {

    if (!email.value.trim()) {

        message.value = "Введите Email";

        return;

    }

    try {

        const response = await forgotPassword(email.value);

        message.value = response.message;

    } catch (error: any) {

        message.value =
            error.response?.data?.detail ??
            "Ошибка.";

    }

}

</script>