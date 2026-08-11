import { EthernetPortIcon } from "lucide-vue-next";
import api from "./axios";

export interface RegisterRequest {
    username: string;
    email: string;
    password: string;
}

export interface LoginRequest {
    login: string;
    password: string;
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
    await api.post("/auth/logout");
}

export async function refresh() {
    const response = await api.post("/auth/refresh");

    return response.data;
}

export async function getCurrentUser() {
    const response = await api.get("/users/me");

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