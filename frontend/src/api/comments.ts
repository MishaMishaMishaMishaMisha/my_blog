import api from "./axios";


export type ReactionType =
    | "like"
    | "dislike"
    | "fire"
    | "shit"
    | "laugh";

export interface ReactResponse {
    user_reaction: ReactionType | null;
}


export interface Attachment {
  id: string;
  url: string;
  file_type: string;
  orig_name: string;
}

export interface Comment {
  id: string;
  post_id: string;
  author_id: string;
  parent_id: string | null;
  body: string;
  attachments: Attachment[];
  reactions: Record<string, number>;
  count_replies: number;
  author_username: string;
  created_at: string;
  user_reaction?: ReactionType | null;
}

// Ответ от POST запроса (содержит не все поля)
export interface CreatedCommentResponse {
  id: string;
  post_id: string;
  author_id: string;
  parent_id: string | null;
  body: string;
  author_username: string;
  created_at: string;
}

export interface AddCommentRequest {
  parent_id: string | null;
  body: string;
  files_id: string[];
}

export interface UpdateCommentRequest {
  body?: string | null;
  files_id?: string[] | null;
}



export async function getPostComments(postId: string, limit = 10, offset = 0): Promise<Comment[]> {
  const response = await api.get(`/posts/${postId}/comments`, {
    params: { limit, offset },
  });
  return response.data;
}

export async function getCommentReplies(commentId: string, limit = 10, offset = 0): Promise<Comment[]> {
  const response = await api.get(`/comments/${commentId}/replies`, {
    params: { limit, offset },
  });
  return response.data;
}

export async function addComment(postId: string, body: AddCommentRequest): Promise<CreatedCommentResponse> {
  const response = await api.post(`/posts/${postId}/comments`, body);
  return response.data;
}


// Удаление комментария
export async function deleteComment(commentId: string): Promise<{ message: string }> {
  const response = await api.delete(`/comments/${commentId}`);
  return response.data;
}

// Редактирование комментария
export async function updateComment(commentId: string, body: UpdateCommentRequest): Promise<Comment> {
  const response = await api.patch(`/comments/${commentId}`, body);
  return response.data;
}

// Реакция на комментарий
export async function reactToComment(commentId: string, reactionType: ReactionType): Promise<ReactResponse> {
  const response = await api.post("/comments/react", {
    comment_id: commentId,
    reaction_type: reactionType,
  });
  return response.data;
}