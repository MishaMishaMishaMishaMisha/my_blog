<template>

<header class="header">

    <div
        class="logo"
        @click="router.push('/')"
    >
        Test Blog
    </div>

    <template v-if="!isAuthPage">

        <div class="search-container">
            <input
                v-model="searchQuery"
                type="text"
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

                <button @click="createPost">

                    Создать пост

                </button>

                <span
                    class="username"
                    @click="openProfile"
                >

                    {{ auth.user.username }}

                </span>

                <button @click="logout">

                    Выйти

                </button>

            </template>

            <template v-else>

                <button @click="login">

                    Войти

                </button>

                <button @click="register">

                    Регистрация

                </button>

            </template>

        </div>

    </template>

</header>

</template>

<script setup lang="ts">

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

  if (val.startsWith("#")) {
    const tagName = val.slice(1).trim();
    if (tagName.length >= 3) {
      searchTimeout = window.setTimeout(async () => {
        try {
          foundTags.value = await searchTags(tagName);
        } catch {
          foundTags.value = [];
        }
      }, 300);
      return;
    }
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

  foundTags.value = [];

  if (query.startsWith("#")) {
    const tagName = query.slice(1).trim();
    if (tagName) selectTag(tagName);
  } else {
    searchQuery.value = "";
    router.push({ path: "/search", query: { title: query } });
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

    padding: 15px 30px;

    border-bottom: 1px solid #ddd;
}

.logo{

    font-size:24px;

    font-weight:bold;

    cursor:pointer;

    color:#1976d2;

}

.logo:hover{

    text-decoration:underline;

}

.search-container {
  position: relative;
  display: inline-block;
}
.tag-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ccc;
  border-top: none;
  border-radius: 0 0 8px 8px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.tag-item {
  padding: 8px 12px;
  cursor: pointer;
}
.tag-item:hover {
  background: #f0f0f0;
}

.right{

    display:flex;

    align-items:center;

    gap:12px;

}

.username{

    cursor:pointer;

    color:#1976d2;

    font-weight:bold;

}

.username:hover{

    text-decoration:underline;

}

button{

    cursor:pointer;

}

</style>