import { EthernetPortIcon } from "lucide-vue-next";
import api from "./axios";


// Ключ для хранения ID текущего пользователя
const CURRENT_USER_ID_KEY = "current_user_id";

export interface RegisterRequest {
    username: string;
    email: string;
    password: string;
}

export interface LoginRequest {
    login: string;
    password: string;
}

export function getCurrentUserId(): string | null {
    return localStorage.getItem(CURRENT_USER_ID_KEY);
}

export async function register(data: RegisterRequest) {
    return await api.post("/users/register", {
        username: data.username,
        email: data.email,
        password: data.password,
    });
}

export async function login(data: LoginRequest) {
    const form = new URLSearchParams();

    form.append("username", data.login);
    form.append("password", data.password);

    const response = await api.post(
        "/auth/login",
        form,
        {
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
        }
    );

    return response.data;
}

export async function logout() {
    try {
        await api.post("/auth/logout");
    } finally {
        // Удаляем ID пользователя при выходе (даже если запрос на сервер упал)
        localStorage.removeItem(CURRENT_USER_ID_KEY);
    }
}

export async function refresh() {
    const response = await api.post("/auth/refresh");

    return response.data;
}

export async function getCurrentUser() {
    const response = await api.get("/users/me");

    if (response.data && response.data.id) {
        localStorage.setItem(CURRENT_USER_ID_KEY, String(response.data.id));
    }

    return response.data;
}


export async function verifyEmail(token: string) {

    //const response = await api.get("/auth/verify-email?token={token}")
    const response = await api.get("/auth/verify-email", {
        params: {
            token,
        },
    });

    return response.data;
}

export async function forgotPassword(email: string) {

    const response = await api.post(
        "/auth/forgot-password",
        {
            user_email: email,
        }
    );

    return response.data;
}

export async function resetPassword(
    token: string,
    newPassword: string,
) {

    const response = await api.post(
        "/auth/reset-password",
        {
            token,
            new_password: newPassword,
        }
    );

    return response.data;
}