<template>

<div
    v-if="post"
>

    <h1>

        {{ post.title }}

    </h1>

    <div
        v-if="auth.user?.id === post.author_id"
        class="actions"
    >

        <button
            @click="editPost"
        >

            Редактировать

        </button>

        <button
            @click="removePost"
        >

            Удалить

        </button>

    </div>

    <p>

        {{ formatDate(post.created_at) }}

    </p>

    <p>

        Автор

        <span
            class="author"
            @click="openAuthor"
        >

            {{ post.author_username }}

        </span>

    </p>


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


    <hr>

    <div
        v-html="renderBody"
    ></div>

    <hr>

    <div class="reactions">

        <div
            v-for="(icon,type) in reactionIcons"
            :key="type"
            class="reaction"
            :class="{
                active:
                    post?.user_reaction===type
            }"
            @click="react(type)"
        >

            {{ icon }}

            {{ post?.reactions[type] ?? 0 }}

        </div>

    </div>

    <br>

    <div>

        👁

        {{ post.views_count }}

        •

        💬

        {{ post.comments_count }}

    </div>

    <hr>

    <h2>Комментарии ({{ post?.comments_count ?? 0 }})</h2>

    <button
    v-if="post.comments_count > 0 && !commentsVisible"
    @click="loadComments"
    >
    {{ loadingComments ? 'Загрузка...' : 'Показать комментарии' }}
    </button>

    <CommentEditor
        v-if="auth.user"
        :post-id="post.id"
        @created="onCommentCreated"
    />
    <div v-else>
        Чтобы оставить комментарий, необходимо авторизоваться.
    </div>

    <div v-if="commentsVisible" class="comments-list">
        <CommentItem
        v-for="comment in comments"
        :key="comment.id"
        :comment="comment"
        :auth-store="auth"
        @deleted="onCommentDeleted"
        />

        <!-- Кнопка подгрузки новых комментариев -->
        <button
            v-if="hasMoreComments"
            class="btn-load-more"
            :disabled="loadingMoreComments"
            @click="loadMoreComments"
        >
            {{ loadingMoreComments ? 'Загрузка...' : 'Показать ещё комментарии' }}
        </button>

    </div>

</div>

<p
    v-else
>

    Загрузка...

</p>

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

.actions{

    margin:15px 0;

    display:flex;

    gap:10px;

}


.reactions{

    display:flex;

    gap:16px;

    margin-top:20px;

}

.reaction{

    display:flex;

    align-items:center;

    gap:6px;

    cursor:pointer;

    user-select:none;

    transition:.2s;

    padding:6px 10px;

    border-radius:8px;

}

.reaction:hover{

    background:#ececec;

}

.reaction.active{

    background:#1976d2;

    color:white;

    font-weight:bold;

}

.author {
  cursor: pointer;
  transition: text-decoration 0.2s;
}

.author:hover {
  text-decoration: underline;
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