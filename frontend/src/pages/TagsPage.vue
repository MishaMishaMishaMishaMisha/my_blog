<template>
  <div class="tags-page">
    <h2>Все теги</h2>

    <div v-if="loading">Загрузка тегов...</div>

    <div v-else-if="tags.length === 0">Теги пока не созданы.</div>

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
.tags-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 15px;
}
.tag-chip {
  padding: 8px 14px;
  background: #eef4fb;
  color: #1976d2;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}
.tag-chip:hover {
  background: #d0e3f7;
}
</style>