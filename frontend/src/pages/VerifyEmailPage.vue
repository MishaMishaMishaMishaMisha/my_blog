<template>

<h2>Подтверждение Email</h2>

<p>{{ message }}</p>

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