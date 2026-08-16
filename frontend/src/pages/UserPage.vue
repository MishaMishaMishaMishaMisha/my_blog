
<template>
  <div class="profile-container">
    <aside class="sidebar">
      <button 
        class="nav-tab" 
        :class="{ active: activeTab === 'info' }"
        @click="activeTab = 'info'"
      >
        Информация
      </button>
      <button 
        class="nav-tab" 
        :class="{ active: activeTab === 'posts' }"
        @click="activeTab = 'posts'"
      >
        Посты
      </button>
      <button 
        v-if="isMyProfile" 
        class="nav-tab" 
        :class="{ active: activeTab === 'drafts' }"
        @click="activeTab = 'drafts'"
      >
        Черновики
      </button>
      <button 
        v-if="isMyProfile" 
        class="nav-tab" 
        :class="{ active: activeTab === 'settings' }"
        @click="activeTab = 'settings'"
      >
        Настройки
      </button>
    </aside>

    <main class="content">
      <div v-if="loading" class="state-msg">
        Загрузка...
      </div>

      <template v-else-if="profile">
        <!-- Вкладка: Информация -->
        <div v-if="activeTab === 'info'" class="tab-content">
          <div class="user-header">
            <h2>
              {{ profile.username }}
              <span v-if="profile.is_verified" class="verified-badge" title="Аккаунт подтвержден">✔</span>
              <AdminBadge :role="profile.role" />
            </h2>
            <p class="last-seen">{{ formatLastSeen(profile.last_seen) }}</p>
          </div>

          <div class="info-grid">
            <div class="info-card">
              <span class="info-label">Дата регистрации</span>
              <span class="info-value">{{ formatDate(profile.created_at) }}</span>
            </div>
            <div class="info-card">
              <span class="info-label">Опубликовано постов</span>
              <span class="info-value">{{ profile.posts_count }}</span>
            </div>
            <div class="info-card">
              <span class="info-label">Оставлено комментариев</span>
              <span class="info-value">{{ profile.comments_count }}</span>
            </div>
          </div>
        </div>

        <!-- Вкладка: Посты -->
        <div v-else-if="activeTab === 'posts'" class="tab-content">
          <div class="posts-list">
            <div v-for="post in posts" :key="post.id" class="post-wrapper">
              <PostCard :post="post" />
              <div v-if="isMyProfile" class="post-actions">
                <button class="btn btn-sm btn-outline" @click="editPost(post.id)">
                  Редактировать
                </button>
                <button class="btn btn-sm btn-danger-outline" @click="handleDeletePost(post.id)">
                  Удалить
                </button>
              </div>
            </div>
          </div>

          <div class="pagination">
            <button
              v-if="posts.length < totalCount"
              class="btn-more"
              @click="loadPosts(false)"
            >
              Показать еще
            </button>
          </div>
        </div>

        <!-- Вкладка: Черновики -->
        <div v-else-if="activeTab === 'drafts'" class="tab-content">
          <h3>Черновики</h3>

          <div v-if="drafts.length === 0" class="state-msg">
            Нет черновиков.
          </div>

          <div class="drafts-list" v-else>
            <div
              v-for="draft in drafts"
              :key="draft.id"
              class="draft-card"
            >
              <div class="draft-info">
                <h4>{{ draft.title || "Без названия" }}</h4>
                <small>Изменено: {{ new Date(draft.updated_at).toLocaleString() }}</small>
              </div>

              <div class="draft-buttons">
                <button class="btn btn-sm btn-primary" @click="openDraft(draft)">
                  Продолжить
                </button>
                <button class="btn btn-sm btn-danger-outline" @click="removeDraft(draft.id)">
                  Удалить
                </button>
              </div>
            </div>
          </div>
        </div>


        <!-- Вкладка: Настройки -->
        <div v-else-if="activeTab === 'settings'" class="tab-content settings-tab">
          <h3>Настройки профиля</h3>

          <!-- Блок 1: Смена никнейма -->
          <div class="settings-section">
            <div class="settings-group">
              <label class="setting-label">Никнейм</label>
              <div class="current-value">Текущий: <strong>{{ auth.user?.username }}</strong></div>
              <input v-model="newUsername" class="app-input" placeholder="Новый никнейм">
            </div>
            <p v-if="usernameError" class="error-message">{{ usernameError }}</p>
            <button 
              class="btn btn-primary btn-save" 
              :disabled="!canSaveUsername" 
              @click="saveUsername"
            >
              Изменить никнейм
            </button>
            <p v-if="usernameMessage" :class="['settings-msg', { 'error-message': usernameHasError }]">
              {{ usernameMessage }}
            </p>
          </div>

          <hr class="divider">

          <!-- Блок 2: Смена пароля -->
          <div class="settings-section">
            <div class="settings-group">
              <label class="setting-label">Смена пароля</label>
              <input v-model="currentPasswordForPassword" type="password" class="app-input" placeholder="Текущий пароль">
              <input v-model="newPassword" type="password" class="app-input" placeholder="Новый пароль">
              <input v-model="confirmNewPassword" type="password" class="app-input" placeholder="Подтверждение нового пароля">
            </div>
            <p v-if="passwordError" class="error-message">{{ passwordError }}</p>
            <button 
              class="btn btn-primary btn-save" 
              :disabled="!canSavePassword" 
              @click="savePassword"
            >
              Изменить пароль
            </button>
            <p v-if="passwordMessage" :class="['settings-msg', { 'error-message': passwordHasError }]">
              {{ passwordMessage }}
            </p>
          </div>

          <hr class="divider">

          <!-- Блок 3: Смена почты -->
          <div class="settings-section">
            <div class="settings-group">
              <label class="setting-label">Почта</label>
              <div class="current-value">Текущая: <strong>{{ auth.user?.email }}</strong></div>
              <input v-model="newEmail" type="email" class="app-input" placeholder="Новая почта">
              <input v-model="currentPasswordForEmail" type="password" class="app-input" placeholder="Текущий пароль для подтверждения">
            </div>
            <p v-if="emailError" class="error-message">{{ emailError }}</p>
            <button 
              class="btn btn-primary btn-save" 
              :disabled="!canSaveEmail" 
              @click="saveEmail"
            >
              Изменить почту
            </button>
            <p v-if="emailMessage" :class="['settings-msg', { 'error-message': emailHasError }]">
              {{ emailMessage }}
            </p>
          </div>

          <hr class="divider">

          <div class="verification-section">
            <div v-if="auth.user?.is_verified" class="verified-status">
              ✔ Аккаунт подтвержден
            </div>
            <div v-else class="unverified-status">
              <p>Аккаунт не подтвержден</p>
              <button class="btn btn-sm btn-outline" @click="sendVerificationEmail">
                Отправить письмо повторно
              </button>
              <p v-if="verificationMessage" class="settings-msg">{{ verificationMessage }}</p>
            </div>
          </div>

          <hr class="divider">

          <div class="danger-zone">
            <button class="btn btn-danger" @click="removeAccount">
              Удалить аккаунт
            </button>
            <p v-if="dangerMessage" class="settings-msg error-message">{{ dangerMessage }}</p>
          </div>
        </div>
        
      </template>
    </main>
  </div>
</template>




<script setup lang="ts">

import AdminBadge from '@/components/AdminBadge.vue'

import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import {
    getPublicProfile,
    getUserPosts,
    updateUsername,
    updatePassword,
    updateEmail,
    deleteCurrentUser,
    resendVerificationEmail,
} from "@/api/users";
import { deletePost } from "@/api/posts";

import { getCurrentUserId } from "@/api/auth";

import PostCard from "@/components/PostCard.vue";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const profile = ref<any>(null);
const posts = ref<any[]>([]);
const totalCount = ref(0);
const limit = 10;
const offset = ref(0);
const activeTab = ref("info");
const drafts = ref<any[]>([]);

// Поля для формы никнейма
const newUsername = ref("");

// Поля для формы пароля
const currentPasswordForPassword = ref("");
const newPassword = ref("");
const confirmNewPassword = ref("");

// Поля для формы почты
const newEmail = ref("");
const currentPasswordForEmail = ref("");

// Сообщения и статусы для каждого блока отдельно
const usernameMessage = ref("");
const usernameHasError = ref(false);

const passwordMessage = ref("");
const passwordHasError = ref(false);

const emailMessage = ref("");
const emailHasError = ref(false);

const verificationMessage = ref("");
const dangerMessage = ref("");

//const settingsMessage = ref("");

// Валидация для никнейма
const usernameError = computed(() => {
    if (!newUsername.value) return "";
    if (newUsername.value === auth.user?.username) return "Новый никнейм совпадает с текущим.";
    if (newUsername.value.length < 5 || newUsername.value.length > 20) {
        return "Длина никнейма должна быть от 5 до 20 символов.";
    }
    return "";
});

const canSaveUsername = computed(() => {
    return Boolean(newUsername.value) && usernameError.value === "" && newUsername.value !== auth.user?.username;
});

// Валидация для пароля
const passwordError = computed(() => {
    if (!newPassword.value && !currentPasswordForPassword.value && !confirmNewPassword.value) return "";
    if (!currentPasswordForPassword.value) return "Введите текущий пароль.";
    if (newPassword.value.length < 8 || newPassword.value.length > 50) {
        return "Длина пароля должна быть от 8 до 50 символов.";
    }
    if (newPassword.value !== confirmNewPassword.value) {
        return "Пароли не совпадают.";
    }
    return "";
});

const canSavePassword = computed(() => {
    return Boolean(
        currentPasswordForPassword.value &&
        newPassword.value &&
        confirmNewPassword.value &&
        passwordError.value === ""
    );
});

// Валидация для почты
const emailError = computed(() => {
    if (!newEmail.value && !currentPasswordForEmail.value) return "";
    if (newEmail.value === auth.user?.email) return "Новая почта совпадает с текущей.";
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (newEmail.value && !emailRegex.test(newEmail.value)) {
        return "Введите корректный email адрес.";
    }
    if (!currentPasswordForEmail.value) return "Введите текущий пароль для подтверждения.";
    return "";
});

const canSaveEmail = computed(() => {
    return Boolean(
        newEmail.value &&
        currentPasswordForEmail.value &&
        emailError.value === "" &&
        newEmail.value !== auth.user?.email
    );
});

const userId = getCurrentUserId();
const DRAFTS_KEY = userId ? `post_drafts_${userId}` : "post_drafts_guest";

function loadDrafts() {
    const data = JSON.parse(localStorage.getItem(DRAFTS_KEY) ?? "{}");
    drafts.value = Object.values(data).sort(
        (a: any, b: any) => b.updated_at - a.updated_at
    );
}

function removeDraft(id: string) {
    const data = JSON.parse(localStorage.getItem(DRAFTS_KEY) ?? "{}");
    delete data[id];
    localStorage.setItem(DRAFTS_KEY, JSON.stringify(data));
    loadDrafts();
}

function openDraft(draft: any) {
    if (draft.isEditMode) {
        router.push(`/posts/${draft.originalPostId}/edit?draftId=${draft.id}`);
    } else {
        router.push(`/posts/create?draftId=${draft.id}`);
    }
}

function editPost(postId: string) {
    router.push(`/posts/${postId}/edit`);
}

async function handleDeletePost(postId: string) {
    if (!confirm("Вы действительно хотите удалить этот пост?")) {
        return;
    }
    try {
        await deletePost(postId);
        posts.value = posts.value.filter(p => p.id !== postId);
        totalCount.value -= 1;
    } catch (error: any) {
        alert(error.response?.data?.detail ?? "Не удалось удалить пост.");
    }
}

async function loadPosts(reset = true) {
    if (reset) {
        offset.value = 0;
        posts.value = [];
    }

    const response = await getUserPosts(
        route.params.username as string,
        limit,
        offset.value
    );

    totalCount.value = response.total_count;
    posts.value.push(...response.posts);
    offset.value += limit;
}

// Отдельные функции сохранения для каждой секции
async function saveUsername() {
    if (!canSaveUsername.value) return;
    usernameMessage.value = "";
    usernameHasError.value = false;

    try {
        const user = await updateUsername({ username: newUsername.value });
        auth.setUser(user);
        usernameMessage.value = "Никнейм успешно изменен.";
        newUsername.value = "";
        router.replace(`/users/${user.username}`);
    } catch (error: any) {
        usernameHasError.value = true;
        usernameMessage.value =
            error.response?.data?.detail ?? "Не удалось изменить никнейм.";
    }
}

// Сохранение пароля
async function savePassword() {
    if (!canSavePassword.value) return;
    passwordMessage.value = "";
    passwordHasError.value = false;

    try {
        await updatePassword({
            current_password: currentPasswordForPassword.value,
            new_password: newPassword.value,
        });
        passwordMessage.value = "Пароль успешно изменен.";
        currentPasswordForPassword.value = "";
        newPassword.value = "";
        confirmNewPassword.value = "";
    } catch (error: any) {
        passwordHasError.value = true;
        const status = error.response?.status;
        if (status === 401) {
            passwordMessage.value = "Неверный текущий пароль.";
        } else if (status === 404) {
            passwordMessage.value = "Пользователь не найден.";
        } else {
            passwordMessage.value =
                error.response?.data?.detail ?? "Не удалось изменить пароль.";
        }
    }
}

// Сохранение почты
async function saveEmail() {
    if (!canSaveEmail.value) return;
    emailMessage.value = "";
    emailHasError.value = false;

    try {
        const user = await updateEmail({
            new_email: newEmail.value,
            confirm_password: currentPasswordForEmail.value,
        });
        auth.setUser(user);
        emailMessage.value = "Почта успешно изменена. Проверьте почту для подтверждения.";
        newEmail.value = "";
        currentPasswordForEmail.value = "";
    } catch (error: any) {
        emailHasError.value = true;
        const status = error.response?.status;
        if (status === 401) {
            emailMessage.value = "Неверный текущий пароль.";
        } else if (status === 400) {
            emailMessage.value = "Эта почта уже занята.";
        } else if (status === 404) {
            emailMessage.value = "Пользователь не найден.";
        } else {
            emailMessage.value =
                error.response?.data?.detail ?? "Ошибка сервера при смене почты.";
        }
    }
}

async function sendVerificationEmail() {
    try {
        const response = await resendVerificationEmail();
        verificationMessage.value = response.message;
    } catch (error: any) {
        verificationMessage.value =
            error.response?.data?.detail ?? "Ошибка.";
    }
}

async function removeAccount() {
    if (!confirm("Вы действительно хотите удалить аккаунт?")) {
        return;
    }

    try {
        await deleteCurrentUser();
        auth.logout();
        router.push("/");
    } catch (error: any) {
        dangerMessage.value =
            error.response?.data?.detail ?? "Не удалось удалить аккаунт.";
    }
}

const isMyProfile = computed(() => {
    return auth.user?.username === route.params.username;
});

async function loadProfile() {
    loading.value = true;
    try {
        profile.value = await getPublicProfile(
            route.params.username as string
        );

        if (activeTab.value === "posts") {
            await loadPosts();
        }

        if (isMyProfile.value) {
            loadDrafts();
        }
    } finally {
        loading.value = false;
    }
}

function formatDate(value: string) {
    return new Date(value).toLocaleString();
}

function formatLastSeen(value: string) {
    const lastSeen = new Date(value);
    const now = new Date();
    const diffMinutes = (now.getTime() - lastSeen.getTime()) / 1000 / 60;

    if (diffMinutes < 5) {
        return "Online";
    }

    return `Был в сети ${formatDate(value)}`;
}

watch(
    () => activeTab.value,
    async (tab) => {
        if (tab === "posts") {
            await loadPosts();
        }
    }
);

onMounted(loadProfile);
</script>




<style scoped>
.profile-container {
  display: flex;
  gap: 30px;
  max-width: 900px;
  margin: 30px auto;
  padding: 0 15px;
}

/* Sidebar Styling */
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 200px;
  flex-shrink: 0;
}

.nav-tab {
  padding: 10px 16px;
  text-align: left;
  background: transparent;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #555;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-tab:hover {
  background-color: #f0f7ff;
  color: #1976d2;
}

.nav-tab.active {
  background-color: #1976d2;
  color: #ffffff;
}

/* Main Content */
.content {
  flex: 1;
  background: #ffffff;
  border: 1px solid #eaeaea;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.02);
}

.tab-content h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #2c3e50;
  font-size: 20px;
}

.state-msg {
  text-align: center;
  color: #666;
  padding: 30px 0;
}

/* Info Tab */
.user-header {
  margin-bottom: 24px;
}

.user-header h2 {
  margin: 0;
  font-size: 24px;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.verified-badge {
  color: #1976d2;
  font-size: 18px;
}

.last-seen {
  color: #888;
  font-size: 14px;
  margin-top: 4px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.info-card {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #eee;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-label {
  font-size: 12px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

/* Posts Tab */
.posts-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.post-wrapper {
  display: flex;
  flex-direction: column;
}

.post-actions {
  display: flex;
  gap: 8px;
  margin-top: -6px;
  padding: 10px 16px;
  background: #fafafa;
  border: 1px solid #eaeaea;
  border-top: none;
  border-bottom-left-radius: 12px;
  border-bottom-right-radius: 12px;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 25px;
}

/* Drafts Tab */
.drafts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.draft-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid #eaeaea;
  border-radius: 8px;
  background: #fff;
  transition: border-color 0.2s;
}

.draft-card:hover {
  border-color: #d0e3f7;
}

.draft-info h4 {
  margin: 0 0 6px 0;
  font-size: 16px;
  color: #2c3e50;
}

.draft-info small {
  color: #888;
}

.draft-buttons {
  display: flex;
  gap: 8px;
}

/* Settings Tab */
.settings-tab {
  max-width: 500px;
}

.settings-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.setting-label {
  font-weight: 600;
  font-size: 14px;
  color: #2c3e50;
}

.current-value {
  font-size: 13px;
  color: #666;
}

.app-input {
  width: 100%;
  box-sizing: border-box;
  padding: 9px 12px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.app-input:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.15);
}

.app-input + .app-input {
  margin-top: 8px;
}

.error-message {
  color: #d32f2f;
  font-size: 14px;
  margin-bottom: 12px;
}

.divider {
  border: none;
  border-top: 1px solid #eee;
  margin: 24px 0;
}

.verified-status {
  color: #2e7d32;
  font-weight: 500;
}

.unverified-status p {
  margin: 0 0 8px 0;
  color: #d32f2f;
}

.settings-msg {
  margin-top: 16px;
  font-size: 14px;
  color: #1976d2;
}

/* Buttons System */
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

.btn-primary {
  background-color: #1976d2;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1565c0;
}

.btn-primary:disabled {
  background-color: #90caf9;
  cursor: not-allowed;
}

.btn-outline {
  background-color: transparent;
  border-color: #ccc;
  color: #444;
}

.btn-outline:hover {
  background-color: #f5f5f5;
  border-color: #bbb;
}

.btn-danger-outline {
  background-color: transparent;
  border-color: #ffcdd2;
  color: #d32f2f;
}

.btn-danger-outline:hover {
  background-color: #ffebee;
}

.btn-danger {
  background-color: #d32f2f;
  color: white;
}

.btn-danger:hover {
  background-color: #c62828;
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

.btn-more:hover {
  background-color: #1976d2;
  color: #fff;
}
</style>