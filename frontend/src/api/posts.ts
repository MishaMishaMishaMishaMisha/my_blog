//import api from "./axios";

import api from "@/api/axios";


export type ReactionType =
    | "like"
    | "dislike"
    | "fire"
    | "shit"
    | "laugh";

export interface ReactResponse {
    user_reaction: ReactionType | null;
}


export interface Tag {
    id: string;
    name: string;
}

export interface PostPreview {
    id: string;
    author_id: string;
    title: string;
    views_count: number;
    comments_count: number;
    tags: Tag[];
}

export interface PostsResponse {
    total_count: number;
    posts: PostPreview[];
}

export interface GetPostsParams {
    limit?: number;
    offset?: number;
    sort?: "new" | "popular";
    period?: "day" | "week" | "month" | "year" | "all_time";
}

export async function getPosts(params: GetPostsParams) {
    const response = await api.get<PostsResponse>("/posts", {
        params,
    });

    return response.data;
}

export async function createPost(data: any) {

    const response = await api.post("/posts", data);

    return response.data;

}

export async function searchTags(name: string) {

    const response = await api.get(
        "/posts/tags/search",
        {
            params: {
                name,
            },
        },
    );

    return response.data;

}

export async function getPost(postId: string) {

    const response = await api.get(`/posts/${postId}`);

    return response.data;

}

export async function deletePost(postId: string) {

    const response = await api.delete(`/posts/${postId}`);

    return response.data;

}

export async function updatePost(
    postId: string,
    data: {
        title?: string;
        body?: string;
        tags: { id: string | null; name: string }[];
        files_id: string[];
    },
) {

    const response = await api.put(
        `/posts/${postId}`,
        data,
    );

    return response.data;

}

export async function reactToPost(
    postId: string,
    reactionType: ReactionType,
): Promise<ReactResponse> {

    const response = await api.post(
        "/posts/react",
        {
            post_id: postId,
            reaction_type: reactionType,
        },
    );

    return response.data;

}


// Поиск постов по названию
export async function searchPostsByTitle(title: string, limit = 10, offset = 0): Promise<PostsResponse> {
  const response = await api.get("/posts/search", {
    params: { title, limit, offset },
  });
  return response.data;
}

// Поиск постов по тегу
export async function searchPostsByTag(tag: string, limit = 10, offset = 0): Promise<PostsResponse> {
  const response = await api.get("/posts/search-with-tag", {
    params: { tag, limit, offset },
  });
  return response.data;
}

// Получение всех существующих тегов
export async function getAllTags(): Promise<Tag[]> {
  const response = await api.get("/posts/tags");
  return response.data;
}


