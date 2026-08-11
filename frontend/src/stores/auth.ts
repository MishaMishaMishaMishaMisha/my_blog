import { defineStore } from "pinia";

export interface User {
    id: string;
    username: string;
    email: string;
    role: "user" | "admin";
    is_active: boolean;
    is_verified: boolean;
    last_login: string;
    last_seen: string;
}

export const useAuthStore = defineStore("auth", {
    state: () => ({
        accessToken: localStorage.getItem("access_token") ?? "",
        user: null as User | null,
    }),

    getters: {
        isAuthenticated: (state) => state.accessToken.length > 0,
    },

    actions: {
        setAccessToken(token: string) {
            this.accessToken = token;
            localStorage.setItem("access_token", token);
        },

        clearAccessToken() {
            this.accessToken = "";
            localStorage.removeItem("access_token");
        },

        setUser(user: User) {
            this.user = user;
        },

        clearUser() {
            this.user = null;
        },

        logout() {
            this.clearAccessToken();
            this.clearUser();
        },
    },
});