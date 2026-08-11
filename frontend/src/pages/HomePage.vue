<template>

<div class="container">

    <div class="controls">

        <select v-model="sort">

            <option value="new">
                Последние
            </option>

            <option value="popular">
                Популярные
            </option>

        </select>

        <select
            v-if="sort === 'popular'"
            v-model="period"
        >
            <option value="day">За день</option>
            <option value="week">За неделю</option>
            <option value="month">За месяц</option>
            <option value="year">За год</option>
            <option value="all_time">За всё время</option>
        </select>

    </div>

    <PostCard
        v-for="post in posts"
        :key="post.id"
        :post="post"
    />

    <button
        v-if="posts.length < totalCount"
        @click="loadMore"
    >
        Показать ещё
    </button>

</div>

</template>

<script setup lang="ts">

import { ref, onMounted, watch } from "vue";

import Navbar from "@/components/Navbar.vue";
import PostCard from "@/components/PostCard.vue";

import { getPosts } from "@/api/posts";

const posts = ref([]);

const totalCount = ref(0);

const limit = 10;

const offset = ref(0);

const sort = ref<"new" | "popular">("new");

const period = ref<"day" | "week" | "month" | "year" | "all_time">("all_time");

async function loadPosts(reset = true) {

    if (reset) {
        offset.value = 0;
    }

    const data = await getPosts({
        limit,
        offset: offset.value,
        sort: sort.value,
        period: period.value,
    });

    totalCount.value = data.total_count;

    if (reset) {
        posts.value = data.posts;
    } else {
        posts.value.push(...data.posts);
    }
}

async function loadMore() {
    offset.value += limit;
    await loadPosts(false);
}

watch([sort, period], () => loadPosts());

onMounted(() => loadPosts());

</script>

<style scoped>

.container {
    width: 900px;
    margin: auto;
}

.controls {
    margin: 25px 0;
}

</style>