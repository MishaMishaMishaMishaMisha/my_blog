import { createRouter, createWebHistory } from "vue-router";
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


const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: "/",
            component: HomePage,
        },
        {
            path: "/login",
            component: LoginPage,
        },
        {
            path: "/register",
            component: RegisterPage,
        },

        {
            path: "/auth/verify-email",
            component: VerifyEmailPage,
        },
        {
            path: "/forgot-password",
            component: ForgotPasswordPage,
        },
        {
            path: "/reset-password",
            component: ResetPasswordPage,
        },

        {
            path: "/users/:username",
            component: UserPage,
        },

        {
            path: "/posts/create",
            component: CreatePostPage,
        },

        {
            path: "/posts/:id",
            component: PostPage,
        },
        {
            path: "/posts/:id/edit",
            component: CreatePostPage,
        },

        {
            path: "/tags",
            name: "Tags",
            component: () => TagsPage,
        },
        {
            path: "/search",
            name: "Search",
            component: () => SearchResultsPage,
        }
        
    ],
});

export default router;