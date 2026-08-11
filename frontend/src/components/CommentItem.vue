<template>
  <div class="comment">
    <div class="comment-header">
      <b class="author" @click="router.push(`/users/${currentComment.author_username}`)">
        {{ currentComment.author_username }}
      </b>
      <span class="created-at">
        {{ new Date(currentComment.created_at).toLocaleString() }}
      </span>
    </div>

    <!-- Показ редактора, если комментарий в режиме редактирования -->
    <CommentEditor
      v-if="showEditEditor"
      :post-id="currentComment.post_id"
      :initial-comment="currentComment"
      @updated="onCommentUpdated"
      @cancel="showEditEditor = false"
    />

    <template v-else>
      <p>{{ currentComment.body }}</p>

      <!-- Вложения -->
      <div v-if="currentComment.attachments?.length" class="attachments">
        <img
          v-for="file in currentComment.attachments"
          :key="file.id"
          :src="api + file.url"
          class="image"
        />
      </div>

      <!-- Реакции -->
      <div class="reactions">
        <div
          v-for="(icon, type) in reactionIcons"
          :key="type"
          class="reaction"
          :class="{ active: currentComment.user_reaction === type }"
          @click="react(type)"
        >
          {{ icon }} {{ currentComment.reactions?.[type] ?? 0 }}
        </div>
      </div>

      <!-- Кнопки действия -->
      <div class="comment-actions">
        <button v-if="authStore?.user" class="btn-link" @click="showReplyEditor = !showReplyEditor">
          Ответить
        </button>

        <!-- Кнопки Редактировать / Удалить для автора комментария -->
        <template v-if="authStore?.user && authStore.user.id === currentComment.author_id">
          <button class="btn-link" @click="showEditEditor = true">
            Редактировать
          </button>
          <button class="btn-link danger" @click="onDelete">
            Удалить
          </button>
        </template>

        <button v-if="repliesCount > 0" class="btn-link" @click="toggleReplies">
          {{ repliesVisible ? 'Скрыть ответы' : `Показать ответы (${repliesCount})` }}
        </button>
      </div>
    </template>

    <!-- Форма ответа -->
    <CommentEditor
      v-if="showReplyEditor"
      :post-id="currentComment.post_id"
      :parent-id="currentComment.id"
      @created="onReplyCreated"
      @cancel="showReplyEditor = false"
    />

    <!-- Дерево ответов -->
    <div v-if="repliesVisible" class="replies-tree">
      <div v-if="loadingReplies">Загрузка ответов...</div>
      <CommentItem
        v-for="reply in replies"
        :key="reply.id"
        :comment="reply"
        :auth-store="authStore"
        @deleted="onReplyDeleted"
      />

        <!-- Кнопка подгрузки следующих ответов -->
        <button
            v-if="hasMoreReplies"
            class="btn-link load-more-replies"
            :disabled="loadingMoreReplies"
            @click="loadMoreReplies"
        >
            {{ loadingMoreReplies ? 'Загрузка...' : 'Показать ещё ответы' }}
        </button>

    </div>
  </div>
</template>



<script setup lang="ts">

import { ref } from "vue";
import type { Comment } from "@/api/comments";
import CommentEditor from "@/components/CommentEditor.vue";
import { getCommentReplies, deleteComment, reactToComment } from "@/api/comments";
import type { ReactionType } from "@/api/posts";

import { useRouter } from "vue-router";

const router = useRouter();

const REPLIES_LIMIT = 10;
const hasMoreReplies = ref(false);
const loadingMoreReplies = ref(false);


const props = defineProps<{
  comment: Comment;
  authStore?: any; // Передаем состояние авторизации для отображения кнопки "Ответить"
}>();

const emit = defineEmits<{
  deleted: [commentId: string];
}>();

const api = import.meta.env.VITE_API_URL;

const showReplyEditor = ref(false);
const repliesVisible = ref(false);
const loadingReplies = ref(false);
const replies = ref<Comment[]>([]);
const repliesCount = ref(props.comment.count_replies);
const showEditEditor = ref(false);
const reacting = ref(false);
const currentComment = ref<Comment>({ ...props.comment });

const reactionIcons = {
  like: "👍",
  dislike: "👎",
  fire: "🔥",
  shit: "💩",
  laugh: "😂",
} as const;


function openAuthor() {
  router.push(`/users/${props.comment.author_username}`);
}

// Реакция на комментарий
async function react(type: ReactionType) {
  if (!props.authStore?.user) {
    alert("Чтобы оставлять реакции, необходимо авторизоваться.");
    return;
  }
  if (reacting.value) return;

  reacting.value = true;
  try {
    const oldReaction = currentComment.value.user_reaction;
    const response = await reactToComment(currentComment.value.id, type);

    currentComment.value.user_reaction = response.user_reaction;

    // Инициализируем реакции, если объекта не было
    if (!currentComment.value.reactions) {
      currentComment.value.reactions = {};
    }

    // Уменьшаем счетчик старой реакции
    if (oldReaction && currentComment.value.reactions[oldReaction]) {
      currentComment.value.reactions[oldReaction]--;
    }

    // Увеличиваем счетчик новой реакции
    if (response.user_reaction) {
      currentComment.value.reactions[response.user_reaction] =
        (currentComment.value.reactions[response.user_reaction] ?? 0) + 1;
    }
  } catch (e) {
    console.error(e);
  } finally {
    reacting.value = false;
  }
}

// Удаление
async function onDelete() {
  if (!confirm("Вы уверены, что хотите удалить комментарий?")) return;

  try {
    await deleteComment(currentComment.value.id);
    emit("deleted", currentComment.value.id);
  } catch (e: any) {
    alert(e.response?.data?.detail ?? "Ошибка при удалении");
  }
}

// Редактирование
function onCommentUpdated(updated: Comment) {
  currentComment.value = { ...currentComment.value, ...updated };
  showEditEditor.value = false;
}

// Удаление вложенного ответа
function onReplyDeleted(replyId: string) {
  replies.value = replies.value.filter((r) => r.id !== replyId);
  repliesCount.value = Math.max(0, repliesCount.value - 1);
}

async function toggleReplies() {
  if (repliesVisible.value) {
    repliesVisible.value = false;
    return;
  }

  if (replies.value.length === 0) {
    loadingReplies.value = true;
    try {
      const data = await getCommentReplies(props.comment.id, REPLIES_LIMIT, 0);
      replies.value = data;
      hasMoreReplies.value = data.length === REPLIES_LIMIT;
    } catch {
      alert("Не удалось загрузить ответы");
    } finally {
      loadingReplies.value = false;
    }
  }

  repliesVisible.value = true;
}

async function loadMoreReplies() {
  if (loadingMoreReplies.value) return;

  loadingMoreReplies.value = true;
  try {
    const offset = replies.value.length;
    const data = await getCommentReplies(props.comment.id, REPLIES_LIMIT, offset);
    
    replies.value.push(...data);
    hasMoreReplies.value = data.length === REPLIES_LIMIT;
  } catch {
    alert("Не удалось подгрузить ответы");
  } finally {
    loadingMoreReplies.value = false;
  }
}

function onReplyCreated(newReply: Comment) {
  showReplyEditor.value = false;
  repliesVisible.value = true;
  replies.value.push(newReply); // Новый ответ добавляем в конец списка ответов
  repliesCount.value++;
}
</script>

<style scoped>
.comment {
  border-bottom: 1px solid #ddd;
  padding: 15px 0;
}
.image {
  max-width: 300px;
  display: block;
  margin-top: 10px;
}
.comment-actions {
  margin-top: 8px;
  display: flex;
  gap: 12px;
}
.btn-link {
  background: none;
  border: none;
  color: #0066cc;
  cursor: pointer;
  padding: 0;
  font-size: 0.9em;
}
.btn-link:hover {
  text-decoration: underline;
}
.replies-tree {
  margin-left: 20px;
  border-left: 2px solid #eee;
  padding-left: 10px;
  margin-top: 10px;
}

.comment-header {
  display: flex;
  gap: 10px;
  align-items: center;
}
.created-at {
  font-size: 0.8em;
  color: #888;
}

.author {
  cursor: pointer;
}

.author:hover {
  text-decoration: underline;
}


.reactions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.reaction {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  user-select: none;
  transition: 0.2s;
  background: #f0f0f0;
}
.reaction:hover {
  background: #e0e0e0;
}
.reaction.active {
  background: #1976d2;
  color: white;
  font-weight: bold;
}
.btn-link.danger {
  color: #cc0000;
}

.btn-load-more {
  display: block;
  margin: 15px auto 0;
  padding: 8px 16px;
  cursor: pointer;
}
.load-more-replies {
  margin-top: 8px;
  font-weight: bold;
}

</style>