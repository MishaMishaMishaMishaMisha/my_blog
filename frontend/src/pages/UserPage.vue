<template>
<div class="profile">
    <aside class="sidebar">
        <button @click="activeTab = 'info'">
            Информация
        </button>
        <button @click="activeTab = 'posts'">
            Посты
        </button>
        <button v-if="isMyProfile" @click="activeTab = 'drafts'">
            Черновики
        </button>
        <button v-if="isMyProfile" @click="activeTab = 'settings'">
            Настройки
        </button>
    </aside>

    <main class="content">
        <template v-if="loading">
            Загрузка...
        </template>

        <template v-else-if="profile">
            <div v-if="activeTab === 'info'">
                <h2>
                    {{ profile.username }}
                    <span v-if="profile.is_verified">✔</span>
                </h2>
                <p>Зарегистрирован: {{ formatDate(profile.created_at) }}</p>
                <p>{{ formatLastSeen(profile.last_seen) }}</p>
                <p>Постов: {{ profile.posts_count }}</p>
                <p>Комментариев: {{ profile.comments_count }}</p>
            </div>

            <div v-else-if="activeTab === 'posts'">
                <div v-for="post in posts" :key="post.id" class="post-wrapper">
                    <PostCard :post="post" />
                    <div v-if="isMyProfile" class="post-actions">
                        <button @click="editPost(post.id)">Редактировать</button>
                        <button @click="handleDeletePost(post.id)">Удалить</button>
                    </div>
                </div>

                <button
                    v-if="posts.length < totalCount"
                    @click="loadPosts(false)"
                >
                    Показать еще
                </button>
            </div>

            <div v-else-if="activeTab === 'drafts'">
                <h3>Черновики</h3>
                <div v-if="drafts.length === 0">
                    Нет черновиков.
                </div>

                <div
                    v-for="draft in drafts"
                    :key="draft.id"
                    class="draft-card"
                >
                    <h4>{{ draft.title || "Без названия" }}</h4>
                    <small>{{ new Date(draft.updated_at).toLocaleString() }}</small>
                    <div class="draft-buttons">
                        <button @click="openDraft(draft)">
                            Продолжить
                        </button>
                        <button @click="removeDraft(draft.id)">
                            Удалить
                        </button>
                    </div>
                </div>
            </div>

            <div v-else>
                <h3>Настройки</h3>
                <div>
                    <h4>Никнейм</h4>
                    <p>{{ auth.user?.username }}</p>
                    <input v-model="newUsername" placeholder="Новый никнейм">
                </div>

                <div>
                    <h4>Почта</h4>
                    <p>{{ auth.user?.email }}</p>
                    <input v-model="newEmail" type="email" placeholder="Новая почта">
                </div>

                <div>
                    <h4>Пароль</h4>
                    <input v-model="newPassword" type="password" placeholder="Новый пароль">
                    <br>
                    <input v-model="confirmPassword" type="password" placeholder="Подтверждение пароля">
                </div>

                <p v-if="validationError" class="error-message">
                    {{ validationError }}
                </p>

                <button :disabled="!canSave" @click="saveSettings">
                    Сохранить изменения
                </button>

                <hr>

                <div v-if="auth.user?.is_verified">
                    ✔ Аккаунт подтвержден
                </div>
                <div v-else>
                    <p>Аккаунт не подтвержден</p>
                    <button @click="sendVerificationEmail">
                        Отправить письмо повторно
                    </button>
                </div>

                <hr>

                <button @click="removeAccount">
                    Удалить аккаунт
                </button>

                <p>{{ settingsMessage }}</p>
            </div>
        </template>
    </main>
</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import {
    getPublicProfile,
    getUserPosts,
    updateCurrentUser,
    deleteCurrentUser,
    resendVerificationEmail,
} from "@/api/users";
import { deletePost } from "@/api/posts"; // Импортируйте deletePost из вашего API постов

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

const newUsername = ref("");
const newEmail = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const settingsMessage = ref("");

const validationError = computed(() => {
    if (newUsername.value) {
        if (newUsername.value.length < 5 || newUsername.value.length > 20) {
            return "Длина никнейма должна быть от 5 до 20 симво символов.";
        }
    }

    if (newEmail.value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(newEmail.value)) {
            return "Введите корректный email адрес.";
        }
    }

    if (newPassword.value || confirmPassword.value) {
        if (newPassword.value.length < 8 || newPassword.value.length > 50) {
            return "Длина пароля должна быть от 8 до 50 символов.";
        }
        if (newPassword.value !== confirmPassword.value) {
            return "Пароли не совпадают.";
        }
    }

    return "";
});

const isAnyFieldFilled = computed(() => {
    return Boolean(
        newUsername.value ||
        newEmail.value ||
        newPassword.value ||
        confirmPassword.value
    );
});

const canSave = computed(() => {
    return isAnyFieldFilled.value && validationError.value === "";
});

const DRAFTS_KEY = "post_drafts";

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

async function saveSettings() {
    if (!canSave.value) return;

    settingsMessage.value = "";
    const data: any = {};

    if (newUsername.value && newUsername.value !== auth.user?.username) {
        data.username = newUsername.value;
    }

    if (newEmail.value && newEmail.value !== auth.user?.email) {
        data.email = newEmail.value;
    }

    if (newPassword.value) {
        data.password = newPassword.value;
    }

    if (Object.keys(data).length === 0) {
        settingsMessage.value = "Нет изменений.";
        return;
    }

    try {
        const user = await updateCurrentUser(data);
        auth.setUser(user);
        settingsMessage.value = "Изменения сохранены.";
        newUsername.value = "";
        newEmail.value = "";
        newPassword.value = "";
        confirmPassword.value = "";

        if (data.username) {
            router.replace(`/users/${user.username}`);
        }
    } catch (error: any) {
        settingsMessage.value =
            error.response?.data?.detail ?? "Не удалось сохранить изменения.";
    }
}

async function sendVerificationEmail() {
    try {
        const response = await resendVerificationEmail();
        settingsMessage.value = response.message;
    } catch (error: any) {
        settingsMessage.value =
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
        settingsMessage.value =
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
.profile {
    display: flex;
    gap: 30px;
    padding: 20px;
}

.sidebar {
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 180px;
}

.sidebar button {
    padding: 10px;
}

.content {
    flex: 1;
}

.error-message {
    color: red;
}

.post-wrapper {
    margin-bottom: 20px;
}

.post-actions {
    display: flex;
    gap: 10px;
    margin-top: 8px;
}

.draft-card {
    border: 1px solid #ddd;
    padding: 12px;
    margin-bottom: 12px;
    border-radius: 8px;
}

.draft-buttons {
    display: flex;
    gap: 10px;
    margin-top: 10px;
}
</style>