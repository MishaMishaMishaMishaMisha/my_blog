<template>
  <div class="post-card" @click="openPost">
    <h3 class="title">
      {{ post.title }}
    </h3>

    <div v-if="post.tags && post.tags.length > 0" class="tags">
      <span
        v-for="tag in post.tags"
        :key="tag.id"
        class="tag-badge"
        @click.stop="goToTag(tag.name)"
      >
        #{{ tag.name }}
      </span>
    </div>

    <div class="footer">
      <div class="stats">
        <span class="stat-item" title="Просмотры">
          <svg class="icon" viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
          </svg>
          {{ post.views_count }}
        </span>

        <span class="stat-item" title="Комментарии">
          <svg class="icon" viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M21.99 4c0-1.1-.89-2-1.99-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4-.01-18zM18 14H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
          </svg>
          {{ post.comments_count }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PostPreview } from "@/api/posts";
import { useRouter } from "vue-router";

const router = useRouter();

const props = defineProps<{
  post: PostPreview;
}>();

function goToTag(tagName: string) {
  router.push({ path: "/search", query: { tag: tagName } });
}

function openPost() {
  router.push(`/posts/${props.post.id}`);
}
</script>

<style scoped>
.post-card {
  padding: 20px;
  background: #ffffff;
  border: 1px solid #eaeaea;
  border-radius: 12px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.post-card:hover {
  border-color: #d0e3f7;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  line-height: 1.4;
  transition: color 0.2s;
}

.post-card:hover .title {
  color: #1976d2;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-badge {
  font-size: 13px;
  color: #1976d2;
  background-color: #f0f7ff;
  padding: 3px 8px;
  border-radius: 6px;
  font-weight: 500;
  transition: background-color 0.2s, color 0.2s;
  user-select: none;
}

.tag-badge:hover {
  background-color: #1976d2;
  color: #ffffff;
}

.footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid #f5f5f5;
  font-size: 13px;
  color: #888;
}

.stats {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon {
  fill: #888;
}
</style>