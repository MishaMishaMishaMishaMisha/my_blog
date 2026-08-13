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
      <p class="comment-body">{{ currentComment.body }}</p>

      <!-- Вложения -->
      <div v-if="currentComment.attachments?.length" class="attachments">
        <template v-for="file in currentComment.attachments" :key="file.id">
          <!-- Если это видео -->
          <video
            v-if="file.file_type === 'video' || file.url.match(/\.(mp4|webm|ogg|mov)$/i)"
            :src="api + file.url"
            controls
            class="attachment-video"
          ></video>

          <!-- Если это изображение или gif -->
          <img
            v-else
            :src="api + file.url"
            class="attachment-image"
          />
        </template>
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
          <span>{{ icon }}</span>
          <span>{{ currentComment.reactions?.[type] ?? 0 }}</span>
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

        <button v-if="repliesCount > 0" class="btn-link btn-toggle-replies" @click="toggleReplies">
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
      <div v-if="loadingReplies" class="state-msg">Загрузка ответов...</div>
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
  border-bottom: 1px solid #f0f0f0;
  padding: 16px 0;
}

.comment:last-child {
  border-bottom: none;
}

.comment-header {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 6px;
}

.author {
  color: #2c3e50;
  cursor: pointer;
  font-size: 14px;
}

.author:hover {
  color: #1976d2;
  text-decoration: underline;
}

.created-at {
  font-size: 12px;
  color: #888;
}

.comment-body {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #333;
  line-height: 1.5;
  white-space: pre-wrap;
}

.attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}

.attachment-image {
  max-width: 260px;
  max-height: 200px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #eee;
}

.reactions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.reaction {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 3px 8px;
  border-radius: 12px;
  user-select: none;
  transition: background 0.2s;
  background: #f0f2f5;
  font-size: 13px;
  color: #555;
}

.reaction:hover {
  background: #e4e6eb;
}

.reaction.active {
  background: #1976d2;
  color: #ffffff;
  font-weight: 600;
}

.comment-actions {
  margin-top: 10px;
  display: flex;
  gap: 14px;
}

.btn-link {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  padding: 0;
  font-size: 13px;
  font-weight: 500;
  transition: color 0.2s;
}

.btn-link:hover {
  color: #1976d2;
  text-decoration: underline;
}

.btn-link.danger {
  color: #d32f2f;
}

.btn-link.danger:hover {
  color: #b71c1c;
}

.btn-toggle-replies {
  color: #1976d2;
}

.replies-tree {
  margin-left: 16px;
  border-left: 2px solid #e3f2fd;
  padding-left: 14px;
  margin-top: 12px;
}

.state-msg {
  font-size: 13px;
  color: #888;
  padding: 8px 0;
}

.load-more-replies {
  margin-top: 10px;
  color: #1976d2;
  font-weight: 600;
}
</style>