<template>
  <div class="container">
    <div class="header-section">
      <div class="controls">
        <select v-model="sort" class="select-input">
          <option value="new">Последние</option>
          <option value="popular">Популярные</option>
        </select>

        <select
          v-if="sort === 'popular'"
          v-model="period"
          class="select-input"
        >
          <option value="day">За день</option>
          <option value="week">За неделю</option>
          <option value="month">За месяц</option>
          <option value="year">За год</option>
          <option value="all_time">За всё время</option>
        </select>
      </div>

      <div class="total-count">
        Найдено постов: <strong>{{ totalCount }}</strong>
      </div>
    </div>

    <div class="posts-list">
      <PostCard
        v-for="post in posts"
        :key="post.id"
        :post="post"
      />
    </div>

    <div class="pagination">
      <button
        v-if="posts.length < totalCount"
        class="btn-more"
        @click="loadMore"
      >
        Показать ещё
      </button>
    </div>
  </div>
</template>




<script setup lang="ts">

import { ref, onMounted, watch } from "vue";

import Navbar from "@/components/Navbar.vue";
import PostCard from "@/components/PostCard.vue";

import type { PostPreview } from '@/api/posts'

import { getPosts } from "@/api/posts";

//const posts = ref([]);
const posts = ref<PostPreview[]>([]);

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
  max-width: 800px;
  margin: 30px auto;
  padding: 0 15px;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.controls {
  display: flex;
  gap: 10px;
}

.select-input {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 6px;
  background-color: #fff;
  font-size: 14px;
  outline: none;
  cursor: pointer;
}

.select-input:focus {
  border-color: #1976d2;
}

.total-count {
  font-size: 14px;
  color: #666;
}

.posts-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 25px;
}

.btn-more {
  padding: 10px 24px;
  background-color: #fff;
  border: 1px solid #1976d2;
  color: #1976d2;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-more:hover {
  background-color: #1976d2;
  color: #fff;
}
</style>