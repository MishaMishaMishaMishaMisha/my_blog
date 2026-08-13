<template>
  <div class="post-page-container">
    <div v-if="post" class="post-card">
      
      <!-- Заголовок и Авторизованные Действия -->
      <div class="post-header">
        <h1 class="post-title">{{ post.title }}</h1>
        <div v-if="auth.user?.id === post.author_id" class="post-actions">
          <button class="btn btn-sm btn-outline" @click="editPost">
            Редактировать
          </button>
          <button class="btn btn-sm btn-danger-outline" @click="removePost">
            Удалить
          </button>
        </div>
      </div>

      <!-- Мета-информация -->
      <div class="post-meta">
        <span class="author" @click="openAuthor">
          👤 {{ post.author_username }}
        </span>
        <span class="bullet">•</span>
        <span class="created-at">{{ formatDate(post.created_at) }}</span>
      </div>

      <!-- Теги -->
      <div v-if="post.tags?.length" class="tags-container">
        <span
          v-for="tag in post.tags"
          :key="tag.id"
          class="tag-badge"
          @click.stop="goToTag(tag.name)"
        >
          #{{ tag.name }}
        </span>
      </div>

      <hr class="divider">

      <!-- Тело поста -->
      <div class="post-body" v-html="renderBody"></div>

      <hr class="divider">

      <!-- Статистика и реакций -->
      <div class="post-footer">
        <div class="reactions">
          <div
            v-for="(icon, type) in reactionIcons"
            :key="type"
            class="reaction"
            :class="{ active: post?.user_reaction === type }"
            @click="react(type)"
          >
            <span>{{ icon }}</span>
            <span>{{ post?.reactions[type] ?? 0 }}</span>
          </div>
        </div>

        <div class="stats">
          <span>👁 {{ post.views_count }}</span>
          <span>💬 {{ post.comments_count }}</span>
        </div>
      </div>

      <!-- Раздел комментариев -->
      <section class="comments-section">
        <h2 class="comments-title">Комментарии ({{ post?.comments_count ?? 0 }})</h2>

        <div class="main-editor-wrapper">
          <CommentEditor
            v-if="auth.user"
            :post-id="post.id"
            @created="onCommentCreated"
          />
          <div v-else class="auth-notice">
            Чтобы оставить комментарий, <router-link to="/login">авторизуйтесь</router-link>.
          </div>
        </div>

        <button
          v-if="post.comments_count > 0 && !commentsVisible"
          class="btn btn-outline btn-show-comments"
          @click="loadComments"
        >
          {{ loadingComments ? 'Загрузка...' : 'Показать комментарии' }}
        </button>

        <div v-if="commentsVisible" class="comments-list">
          <CommentItem
            v-for="comment in comments"
            :key="comment.id"
            :comment="comment"
            :auth-store="auth"
            @deleted="onCommentDeleted"
          />

          <button
            v-if="hasMoreComments"
            class="btn btn-outline btn-load-more"
            :disabled="loadingMoreComments"
            @click="loadMoreComments"
          >
            {{ loadingMoreComments ? 'Загрузка...' : 'Показать ещё комментарии' }}
          </button>
        </div>
      </section>

    </div>

    <div v-else class="loading-state">
      Загрузка поста...
    </div>
  </div>
</template>



<script setup lang="ts">

import { computed, onMounted, ref } from "vue";

import { useRoute, useRouter } from "vue-router";

import { getPost } from "@/api/posts";

import { useAuthStore } from "@/stores/auth";
import { deletePost } from "@/api/posts";

import { reactToPost } from "@/api/posts";

import CommentItem
from "@/components/CommentItem.vue";

import CommentEditor
from "@/components/CommentEditor.vue";

import {
    getPostComments,
} from "@/api/comments";

import type { Comment } from "@/api/comments";



const auth = useAuthStore();

const route = useRoute();

const router = useRouter();

const post = ref<any>();


const LIMIT = 10;
const hasMoreComments = ref(true);
const loadingMoreComments = ref(false);


const reacting = ref(false);

const reactionIcons = {
    like: "👍",
    dislike: "👎",
    fire: "🔥",
    shit: "💩",
    laugh: "😂",
} as const


const comments = ref<Comment[]>([]);

const commentsVisible =
    ref(false);

const loadingComments =
    ref(false);



onMounted(loadPost);


function goToTag(tagName: string) {
  router.push({ path: "/search", query: { tag: tagName } });
}


function onCommentCreated(comment: Comment) {
  if (!commentsVisible.value) {
    commentsVisible.value = true;
  }
  // Новый корневой комментарий добавляем в начало
  comments.value.unshift(comment);

  if (post.value) {
    post.value.comments_count++;
  }
}

function onCommentDeleted(commentId: string) {
  // Фильтруем массив корневых комментариев
  comments.value = comments.value.filter((c) => c.id !== commentId);
  
  // Уменьшаем общий счетчик комментариев у поста
  if (post.value && post.value.comments_count > 0) {
    post.value.comments_count--;
  }
}

async function loadComments() {
  if (commentsVisible.value || !post.value) return;

  loadingComments.value = true;
  try {
    const data = await getPostComments(post.value.id, LIMIT, 0);
    comments.value = data;
    commentsVisible.value = true;
    
    // Если пришло меньше LIMIT, значит больше комментариев нет
    hasMoreComments.value = data.length === LIMIT;
  } catch {
    alert("Ошибка загрузки комментариев.");
  } finally {
    loadingComments.value = false;
  }
}

async function loadMoreComments() {
  if (!post.value || loadingMoreComments.value) return;

  loadingMoreComments.value = true;
  try {
    const offset = comments.value.length;
    const data = await getPostComments(post.value.id, LIMIT, offset);
    
    comments.value.push(...data);
    hasMoreComments.value = data.length === LIMIT;
  } catch {
    alert("Ошибка при подгрузке комментариев.");
  } finally {
    loadingMoreComments.value = false;
  }
}


async function react(type: keyof typeof reactionIcons) {

    if (!auth.user) {

        alert("Чтобы оставлять реакции, необходимо авторизоваться.");

        return;

    }

    if (!post.value || reacting.value) {
        return;
    }

    reacting.value = true;

    try {

        const oldReaction =
            post.value.user_reaction;

        const response =
            await reactToPost(
                post.value.id,
                type,
            );

        post.value.user_reaction =
            response.user_reaction;

        if (oldReaction) {

            post.value.reactions[oldReaction]--;

        }

        if (response.user_reaction) {

            post.value.reactions[
                response.user_reaction
            ]++;

        }

    } catch (e) {

        console.error(e);

    } finally {

        reacting.value = false;

    }

}


async function removePost() {

    if (!confirm("Удалить пост?")) {

        return;

    }

    try {

        await deletePost(post.value.id);

        alert("Пост удален.");

        router.push("/");

    }

    catch {

        alert("Не удалось удалить пост.");

    }

}

function editPost() {

    router.push(`/posts/${post.value.id}/edit`);

}

async function loadPost() {

    try {

        post.value =
            await getPost(
                route.params.id as string,
            );

    }

    catch {

        alert("Пост не найден.");

        router.push("/");

    }

}

function formatDate(date: string) {

    return new Date(date).toLocaleString();

}

function openAuthor() {

    router.push(
        `/users/${post.value.author_username}`,
    );

}

const reactionEmoji: Record<string, string> = {

    like: "👍",

    dislike: "👎",

    fire: "🔥",

    shit: "💩",

    laugh: "😂",

};

const reactionList = computed(() => {

    if (!post.value) {

        return [];

    }

    return Object.entries(
        post.value.reactions,
    ).map(

        ([type, count]) => ({

            type,

            count,

            emoji:
                reactionEmoji[type] ??
                type,

        }),

    );

});

const renderBody = computed(() => {

    if (!post.value) {

        return "";

    }

    let body = post.value.body;

    for (const file of post.value.attachments) {

        const placeholder =
            `[file:${file.id}]`;

        let html = "";

        const fileUrl = file.url.startsWith("http")
            ? file.url
            : `${import.meta.env.VITE_API_URL}${file.url}`;

        if (
            file.file_type === "image" ||
            file.file_type === "gif"
        ) {

            html =
                `<img src="${fileUrl}" style="max-width:700px">`;

        }

        else {

            html =
                `<video controls style="max-width:700px">
                    <source src="${fileUrl}">
                </video>`;

        }

        body =
            body.replaceAll(
                placeholder,
                html,
            );

    }

    return body.replaceAll(
        "\n",
        "<br>",
    );

});

</script>






<style scoped>
.post-page-container {
  max-width: 800px;
  margin: 30px auto;
  padding: 0 15px;
}

.post-card {
  background: #ffffff;
  border: 1px solid #eaeaea;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}

.loading-state {
  text-align: center;
  color: #666;
  padding: 40px 0;
}

.post-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.post-title {
  margin: 0;
  font-size: 26px;
  color: #2c3e50;
  line-height: 1.3;
}

.post-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.post-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 14px;
  color: #666;
}

.author {
  font-weight: 500;
  cursor: pointer;
  color: #2c3e50;
  transition: color 0.2s;
}

.author:hover {
  color: #1976d2;
}

.bullet {
  color: #ccc;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.tag-badge {
  cursor: pointer;
  color: #1976d2;
  background: #f0f7ff;
  padding: 4px 10px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.2s;
}

.tag-badge:hover {
  background: #e3f2fd;
}

.divider {
  border: none;
  border-top: 1px solid #f0f0f0;
  margin: 24px 0;
}

.post-body {
  font-size: 16px;
  line-height: 1.6;
  color: #333;
}

.post-body :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 12px 0;
}

.post-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.reactions {
  display: flex;
  gap: 8px;
}

.reaction {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
  padding: 6px 12px;
  border-radius: 16px;
  background: #f0f2f5;
  font-size: 14px;
}

.reaction:hover {
  background: #e4e6eb;
}

.reaction.active {
  background: #1976d2;
  color: white;
  font-weight: 600;
}

.stats {
  display: flex;
  gap: 16px;
  color: #777;
  font-size: 14px;
}

/* Comments Section */
.comments-section {
  margin-top: 32px;
}

.comments-title {
  font-size: 20px;
  color: #2c3e50;
  margin-bottom: 16px;
}

.main-editor-wrapper {
  margin-bottom: 24px;
}

.auth-notice {
  background: #f8f9fa;
  padding: 14px;
  border-radius: 8px;
  color: #666;
  font-size: 14px;
  text-align: center;
  border: 1px dashed #ccc;
}

.auth-notice a {
  color: #1976d2;
  text-decoration: none;
  font-weight: 500;
}

.auth-notice a:hover {
  text-decoration: underline;
}

.btn-show-comments,
.btn-load-more {
  width: 100%;
  margin-top: 16px;
  padding: 10px;
}

.comments-list {
  margin-top: 16px;
}

/* Button System */
.btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 6px;
}

.btn-outline {
  background-color: transparent;
  border-color: #1976d2;
  color: #1976d2;
}

.btn-outline:hover {
  background-color: #f0f7ff;
}

.btn-danger-outline {
  background-color: transparent;
  border-color: #ffcdd2;
  color: #d32f2f;
}

.btn-danger-outline:hover {
  background-color: #ffebee;
}
</style>