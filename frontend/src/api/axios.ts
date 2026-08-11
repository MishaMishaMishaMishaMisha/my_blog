import axios from "axios";

import { useAuthStore } from "@/stores/auth";


const noRefreshEndpoints = [
    "/auth/login",
    "/auth/refresh",
    "/auth/verify-email",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/users/register"
];


const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL,
    withCredentials: true,
});

api.interceptors.request.use((config) => {
    const auth = useAuthStore();

    if (auth.accessToken) {
        config.headers.Authorization = `Bearer ${auth.accessToken}`;
    }

    return config;
});

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
    if (!refreshPromise) {
        refreshPromise = axios
            .post(
                `${import.meta.env.VITE_API_URL}/auth/refresh`,
                {},
                {
                    withCredentials: true,
                }
            )
            .then((response) => response.data.access_token)
            .finally(() => {
                refreshPromise = null;
            });
    }

    return refreshPromise;
}

api.interceptors.response.use(
    (response) => response,

    async (error) => {
        const auth = useAuthStore();

        const originalRequest = error.config;

        if (!originalRequest) {
            return Promise.reject(error);
        }


        // ==========================================
        // 1. ОБРАБОТКА 403 (Email не подтверждён)
        // ==========================================
        if (error.response?.status === 403) {
            const detail = error.response.data?.detail;

            // Проверяем, что это ошибка именно подтверждения почты
            if (detail === "Please, verify your email to do this") {
                alert("Действие запрещено: пожалуйста, подтвердите ваш email!");
                // При желании можно заменить alert на тост/нотификацию:
                // toast.error("Подтвердите ваш email для выполнения этого действия!");
            } else {
                // Если с сервера пришла другая 403 ошибка
                alert(detail || "Доступ запрещен.");
            }

            return Promise.reject(error);
        }


        // ==========================================
        // 1. ОБРАБОТКА 401 (истек access token)
        // ==========================================
        if (error.response?.status !== 401) {
            return Promise.reject(error);
        }

        const requestUrl = originalRequest.url ?? "";
        if (noRefreshEndpoints.some(url => requestUrl.startsWith(url))) {
            return Promise.reject(error);
        }

        if (originalRequest._retry) {
            auth.logout();
            return Promise.reject(error);
        }

        const authHeader = originalRequest.headers?.Authorization;

        if (!authHeader) {
            return Promise.reject(error);
        }

        if (originalRequest.url === "/auth/refresh") {
            auth.logout();
            return Promise.reject(error);
        }

        originalRequest._retry = true;

        try {
            const accessToken = await refreshAccessToken();

            auth.setAccessToken(accessToken);

            originalRequest.headers.Authorization =
                `Bearer ${accessToken}`;

            return api(originalRequest);

        } catch {

            auth.logout();

            return Promise.reject(error);

        }
    }
);

export default api;