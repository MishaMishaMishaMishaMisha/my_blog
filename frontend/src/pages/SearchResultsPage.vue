<template>
  <div class="search-page">
    <div class="search-header">
      <h2>
        <template v-if="tagParam">Посты по тегу: #{{ tagParam }}</template>
        <template v-else-if="titleParam">Поиск по запросу: "{{ titleParam }}"</template>
        <template v-else>Результаты поиска</template>
      </h2>

      <div v-if="!loading && posts.length > 0" class="total-count">
        Найдено постов: <strong>{{ totalCount }}</strong>
      </div>
    </div>

    <div v-if="loading" class="state-msg">Поиск постов...</div>

    <div v-else-if="posts.length === 0" class="state-msg">
      По вашему запросу ничего не найдено.
    </div>

    <div v-else class="posts-list">
      <PostCard
        v-for="post in posts"
        :key="post.id"
        :post="post"
      />

      <div class="pagination">
        <button
          v-if="hasMore"
          class="btn-more"
          :disabled="loadingMore"
          @click="loadMore"
        >
          {{ loadingMore ? 'Загрузка...' : 'Показать ещё' }}
        </button>
      </div>
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
.search-page {
  max-width: 800px;
  margin: 30px auto;
  padding: 0 15px;
}

.search-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 20px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

h2 {
  margin: 0;
  font-size: 20px;
  color: #2c3e50;
}

.total-count {
  font-size: 14px;
  color: #666;
}

.state-msg {
  text-align: center;
  color: #666;
  margin: 40px 0;
  font-size: 16px;
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

.btn-more:hover:not(:disabled) {
  background-color: #1976d2;
  color: #fff;
}

.btn-more:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>