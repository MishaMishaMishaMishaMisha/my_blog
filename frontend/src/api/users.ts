import api from "./axios";

export async function getPublicProfile(username: string) {

    const response = await api.get(`/users/${encodeURIComponent(username)}`);

    return response.data;

}

export async function getUserPosts(
    username: string,
    limit = 10,
    offset = 0,
) {

    const response = await api.get(
        `/users/${encodeURIComponent(username)}/posts`,
        {
            params: {
                limit,
                offset,
            },
        },
    );

    return response.data;

}

export async function updateCurrentUser(data: {
    username?: string;
    email?: string;
    password?: string;
}) {

    const response = await api.patch("/users/me", data);

    return response.data;

}

export async function deleteCurrentUser() {

    const response = await api.delete("/users/me");

    return response.data;

}

export async function resendVerificationEmail() {

    const response = await api.post(
        "/auth/resend-verification-email",
    );

    return response.data;

}