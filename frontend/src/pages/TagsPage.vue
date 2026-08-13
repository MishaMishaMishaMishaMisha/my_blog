<template>
  <div class="tags-page">
    <div class="page-header">
      <h2>Все теги</h2>
      <div v-if="!loading && tags.length > 0" class="total-count">
        Всего тегов: <strong>{{ tags.length }}</strong>
      </div>
    </div>

    <div v-if="loading" class="state-msg">Загрузка тегов...</div>

    <div v-else-if="tags.length === 0" class="state-msg">
      Теги пока не созданы.
    </div>

    <div v-else class="tags-cloud">
      <div
        v-for="tag in tags"
        :key="tag.id"
        class="tag-chip"
        @click="goToTag(tag.name)"
      >
        #{{ tag.name }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { getAllTags } from "@/api/posts";
import type { Tag } from "@/api/posts";

const router = useRouter();
const tags = ref<Tag[]>([]);
const loading = ref(true);

onMounted(async () => {
  try {
    tags.value = await getAllTags();
  } catch {
    alert("Ошибка загрузки тегов");
  } finally {
    loading.value = false;
  }
});

function goToTag(tagName: string) {
  router.push({ path: "/search", query: { tag: tagName } });
}
</script>

<style scoped>
.tags-page {
  max-width: 800px;
  margin: 30px auto;
  padding: 0 15px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 24px;
  border-bottom: 1px solid #eee;
  padding-bottom: 12px;
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

.tags-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag-chip {
  padding: 8px 16px;
  background: #f0f7ff;
  color: #1976d2;
  border: 1px solid #d0e3f7;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  user-select: none;
}

.tag-chip:hover {
  background: #1976d2;
  color: #ffffff;
  border-color: #1976d2;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(25, 118, 210, 0.2);
}
</style>