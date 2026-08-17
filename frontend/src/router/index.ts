import { createRouter, createWebHistory, 
    type RouteLocationNormalizedLoaded,
    type RouteRecordRaw} from "vue-router";
import HomePage from "@/pages/HomePage.vue";

import LoginPage from "@/pages/LoginPage.vue";
import RegisterPage from "@/pages/RegisterPage.vue";

import VerifyEmailPage from "@/pages/VerifyEmailPage.vue";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage.vue";
import ResetPasswordPage from "@/pages/ResetPasswordPage.vue";

import CreatePostPage from "@/pages/CreatePostPage.vue";

import UserPage from "@/pages/UserPage.vue";

import PostPage from "@/pages/PostPage.vue";

import TagsPage from "@/pages/TagsPage.vue";
import SearchResultsPage from "@/pages/SearchResultsPage.vue";


declare module 'vue-router' {
  interface RouteMeta {
    title?: string | ((route: RouteLocationNormalizedLoaded) => string)
  }
}

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: "/",
            component: HomePage,
            meta: { title: 'MY BLOG' }
        },
        {
            path: "/login",
            component: LoginPage,
            meta: { title: 'Вход в аккаунт' }
        },
        {
            path: "/register",
            component: RegisterPage,
            meta: { title: 'Регистрация' }
        },

        {
            path: "/auth/verify-email",
            component: VerifyEmailPage,
            meta: { title: 'Подтверждение аккаунта' }
        },
        {
            path: "/forgot-password",
            component: ForgotPasswordPage,
            meta: { title: 'Восстановление пароля' }
        },
        {
            path: "/reset-password",
            component: ResetPasswordPage,
            meta: { title: 'Восстановление пароля' }
        },

        {
            path: "/users/:username",
            component: UserPage,
            meta: { title: (route: RouteLocationNormalizedLoaded) => `Профиль: ${route.params.username}` }
        },

        {
            path: "/posts/create",
            component: CreatePostPage,
            meta: { title: 'Создание поста' }
        },

        {
            path: "/posts/:id",
            component: PostPage,
            meta: { title: 'Загрузка...' }
        },
        {
            path: "/posts/:id/edit",
            component: CreatePostPage,
            meta: { title: 'Редактирование поста' }
        },

        {
            path: "/tags",
            name: "Tags",
            component: () => TagsPage,
            meta: { title: 'Теги' }
        },
        {
            path: "/search",
            name: "Search",
            component: () => SearchResultsPage,
            meta: { 
                title: (route) => {
                const queryTitle = route.query.title as string | undefined
                const queryTag = route.query.tag as string | undefined

                if (queryTitle) {
                    return `Поиск: ${queryTitle}`
                }

                if (queryTag) {
                    return `Поиск по тегу: ${queryTag}`
                }

                return 'Поиск'
                }
            }
        }
        
    ],
});


router.beforeEach((to, _from, next) => {
  const defaultTitle = 'MY BLOG'

  if (typeof to.meta.title === 'function') {
    // Вызываем функцию и передаем текущий маршрут 'to'
    document.title = to.meta.title(to) || defaultTitle
  } else if (typeof to.meta.title === 'string') {
    // Если передана обычная строка
    document.title = to.meta.title
  } else {
    // Если meta.title вообще не указан
    document.title = defaultTitle
  }

  next()
})

export default router;