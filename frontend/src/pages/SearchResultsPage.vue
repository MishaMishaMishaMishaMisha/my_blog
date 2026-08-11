<template>
  <div class="search-page">
    <h2>
      <template v-if="tagParam">Посты по тегу: #{{ tagParam }}</template>
      <template v-else-if="titleParam">Поиск по запросу: "{{ titleParam }}"</template>
      <template v-else>Результаты поиска</template>
    </h2>

    <div v-if="loading">Поиск постов...</div>

    <div v-else-if="posts.length === 0">
      По вашему запросу ничего не найдено.
    </div>

    <div v-else class="posts-list">
      <PostCard
        v-for="post in posts"
        :key="post.id"
        :post="post"
      />

      <!-- Кнопка «Показать ещё» для результатов поиска -->
      <button
        v-if="hasMore"
        class="load-more-btn"
        :disabled="loadingMore"
        @click="loadMore"
      >
        {{ loadingMore ? 'Загрузка...' : 'Показать ещё' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useRoute } from "vue-router";
import PostCard from "@/components/PostCard.vue";
import { searchPostsByTitle, searchPostsByTag } from "@/api/posts";
import type { PostPreview } from "@/api/posts";

const route = useRoute();
const LIMIT = 10;

const posts = ref<PostPreview[]>([]);
const totalCount = ref(0);
const loading = ref(false);
const loadingMore = ref(false);

const tagParam = computed(() => route.query.tag as string | undefined);
const titleParam = computed(() => route.query.title as string | undefined);

const hasMore = computed(() => posts.value.length < totalCount.value);

async function fetchResults() {
  loading.value = true;
  posts.value = [];

  try {
    if (tagParam.value) {
      const res = await searchPostsByTag(tagParam.value, LIMIT, 0);
      posts.value = res.posts;
      totalCount.value = res.total_count;
    } else if (titleParam.value) {
      const res = await searchPostsByTitle(titleParam.value, LIMIT, 0);
      posts.value = res.posts;
      totalCount.value = res.total_count;
    }
  } catch {
    alert("Ошибка при поиске.");
  } finally {
    loading.value = false;
  }
}

async function loadMore() {
  if (loadingMore.value) return;

  loadingMore.value = true;
  const offset = posts.value.length;

  try {
    if (tagParam.value) {
      const res = await searchPostsByTag(tagParam.value, LIMIT, offset);
      posts.value.push(...res.posts);
    } else if (titleParam.value) {
      const res = await searchPostsByTitle(titleParam.value, LIMIT, offset);
      posts.value.push(...res.posts);
    }
  } catch {
    alert("Ошибка при подгрузке.");
  } finally {
    loadingMore.value = false;
  }
}

// Перезапрашиваем данные, если пользователь ищет заново с этой же страницы
watch(() => route.query, () => {
  fetchResults();
});

onMounted(() => {
  fetchResults();
});
</script>

<style scoped>
.posts-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 20px;
}
.load-more-btn {
  margin: 10px auto;
  padding: 8px 16px;
  cursor: pointer;
}
</style>