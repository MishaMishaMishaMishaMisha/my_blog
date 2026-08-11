<template>

<Navbar />

<RouterView />

</template>

<script setup lang="ts">

import { RouterView } from "vue-router";
import Navbar from "@/components/Navbar.vue";

import { onMounted } from "vue";
import { useAuthStore } from "@/stores/auth";
import { getCurrentUser } from "@/api/auth";

const auth = useAuthStore();

onMounted(async () => {

    if (!auth.isAuthenticated) {
        return;
    }

    try {

        const user = await getCurrentUser();

        auth.setUser(user);

    } catch {

        auth.logout();

    }

});

</script>