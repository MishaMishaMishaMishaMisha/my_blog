<template>

    <div class="post-card">

        <h3
            class="title"
            @click="openPost"
        >
            {{ post.title }}
        </h3>

        <div class="info">

            👁 {{ post.views_count }}

            •

            💬 {{ post.comments_count }}

        </div>

        <div class="tags">
        <span
            v-for="tag in post.tags"
            :key="tag.id"
            class="tag-badge"
            @click.stop="goToTag(tag.name)"
        >
            #{{ tag.name }}
        </span>
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
    padding: 16px;
    border: 1px solid #ddd;
    border-radius: 8px;
    margin-bottom: 16px;
}

.title {
    margin: 0;
    color: #1976d2;
    cursor: pointer;
    transition: color .2s;
}

.title:hover {
    color: #0d47a1;
    text-decoration: underline;
}

.info {
    color: gray;
    margin-top: 8px;
}



.tag-badge {
  cursor: pointer;
  color: #1976d2;
  margin-right: 6px;
  user-select: none;
}
.tag-badge:hover {
  text-decoration: underline;
}

</style>