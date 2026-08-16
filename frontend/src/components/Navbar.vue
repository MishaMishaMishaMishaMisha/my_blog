<template>
  <header class="header">
    <div class="logo" @click="router.push('/')">
      MY BLOG
    </div>

    <template v-if="!isAuthPage">
      <div class="search-container">
        <input
          v-model="searchQuery"
          type="text"
          class="search-input"
          maxlength="120"
          placeholder="Поиск по названию или #тегу..."
          @keyup.enter="handleSearchSubmit"
        />

        <div v-if="foundTags.length > 0" class="tag-dropdown">
          <div
            v-for="tag in foundTags"
            :key="tag.id"
            class="tag-item"
            @click="selectTag(tag.name)"
          >
            #{{ tag.name }}
          </div>
        </div>
      </div>

      <router-link to="/tags" class="nav-link">Теги</router-link>

      <div class="right">
        <template v-if="auth.user">
          <button class="btn btn-primary" @click="createPost">
            + Создать пост
          </button>

          <span class="username" @click="openProfile">
            {{ auth.user?.username }}
            <AdminBadge :role="auth.user?.role" />
          </span>

          <button class="btn btn-outline" @click="logout">
            Выйти
          </button>
        </template>

        <template v-else>
          <button class="btn btn-outline" @click="login">
            Войти
          </button>

          <button class="btn btn-primary" @click="register">
            Регистрация
          </button>
        </template>
      </div>
    </template>
  </header>
</template>




<script setup lang="ts">

import AdminBadge from '@/components/AdminBadge.vue'

import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

import { computed } from "vue";
import { useRoute } from "vue-router";

import { ref, watch } from "vue";
import { searchTags } from "@/api/posts";
import type { Tag } from "@/api/posts";

const route = useRoute();

const router = useRouter();
const searchQuery = ref("");
const foundTags = ref<Tag[]>([]);
let searchTimeout: number | undefined;

const isAuthPage = computed(() =>
    [
        "/login",
        "/register",
        "/forgot-password",
        "/reset-password",
    ].includes(route.path)
);


const auth = useAuthStore();


// Автокомплит тегов при старте с '#'
watch(searchQuery, (val) => {
  clearTimeout(searchTimeout);
  const trimmedVal = val.trim();

  if (trimmedVal.startsWith("#")) {
    const tagName = trimmedVal.slice(1).trim();
    // Минимум 2, максимум 50 символов для тега
    if (tagName.length >= 2 && tagName.length <= 50) {
      searchTimeout = window.setTimeout(async () => {
        try {
          foundTags.value = await searchTags(tagName);
        } catch {
          foundTags.value = [];
        }
      }, 300);
      return;
    }
  } else if (trimmedVal.length > 0 && trimmedVal.length < 3) {
    // Если введено меньше 3 символов обычного текста, автокомплит не нужен
    foundTags.value = [];
    return;
  }

  foundTags.value = [];
});

function selectTag(tagName: string) {
  foundTags.value = [];
  searchQuery.value = "";
  router.push({ path: "/search", query: { tag: tagName } });
}

function handleSearchSubmit() {
  const query = searchQuery.value.trim();
  if (!query) return;

  if (query.startsWith("#")) {
    const tagName = query.slice(1).trim();
    // Проверка для тега: от 2 до 50 символов
    if (tagName.length >= 2 && tagName.length <= 50) {
      foundTags.value = [];
      selectTag(tagName);
    }
  } else {
    // Проверка для обычного поиска: от 3 до 120 символов
    if (query.length >= 3 && query.length <= 120) {
      foundTags.value = [];
      searchQuery.value = "";
      router.push({ path: "/search", query: { title: query } });
    }
  }
}


function goHome() {

    router.push("/");

}

function login() {

    router.push("/login");

}

function register() {

    router.push("/register");

}

function openProfile() {

    router.push(`/users/${auth.user?.username}`);

}

function createPost() {

    router.push("/posts/create");

}

async function logout() {

    await auth.logout();

    router.push("/");

}

</script>




<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  box-sizing: border-box;
  padding: 12px 30px;
  background-color: #ffffff;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.logo {
  font-size: 22px;
  font-weight: 700;
  cursor: pointer;
  color: #1976d2;
  transition: color 0.2s;
}

.logo:hover {
  color: #1565c0;
}

.search-container {
  position: relative;
  flex: 1;
  max-width: 420px;
  margin: 0 20px;
}

.search-input {
  width: 100%;
  box-sizing: border-box;
  padding: 9px 16px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-input:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.15);
}

.tag-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.tag-item {
  padding: 10px 14px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.15s;
}

.tag-item:hover {
  background: #f5f5f5;
  color: #1976d2;
}

.nav-link {
  text-decoration: none;
  color: #444;
  font-weight: 500;
  margin-right: 15px;
  transition: color 0.2s;
}

.nav-link:hover {
  color: #1976d2;
}

.right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  cursor: pointer;
  color: #1976d2;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.username:hover {
  background-color: #f0f7ff;
}

/* Общий стиль для кнопок в Navbar */
.btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.btn-primary {
  background-color: #1976d2;
  color: white;
}

.btn-primary:hover {
  background-color: #1565c0;
}

.btn-outline {
  background-color: transparent;
  border-color: #1976d2;
  color: #1976d2;
}

.btn-outline:hover {
  background-color: #f0f7ff;
}
</style>