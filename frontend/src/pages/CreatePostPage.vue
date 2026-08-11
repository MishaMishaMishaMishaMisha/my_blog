<template>
<h2>
    {{ editMode ? "Редактирование поста" : "Создание поста" }}
</h2>

<p>Заголовок</p>
<input v-model="title">

<p>Текст</p>
<textarea v-model="body" rows="15"></textarea>

<br><br>

<h3>Теги</h3>
<input v-model="tagInput" placeholder="Введите тег" />

<div v-if="foundTags.length">
    <div
        v-for="tag in foundTags"
        :key="tag.id"
        @click="addExistingTag(tag)"
        style="cursor:pointer"
    >
        {{ tag.name }}
    </div>
</div>

<button v-if="tagInput.trim().length >= 3" @click="createTag">
    Создать "{{ tagInput }}"
</button>

<br><br>

<div>
    <span
        v-for="(tag, index) in selectedTags"
        :key="tag.name"
        style="
            display:inline-block;
            margin-right:8px;
            margin-bottom:6px;
            padding:5px 10px;
            border:1px solid gray;
        "
    >
        {{ tag.name }}
        <button @click="removeTag(index)">×</button>
    </span>
</div>

<br>

<h3>Файлы</h3>
<input
    type="file"
    multiple
    accept="image/*,video/*,.gif"
    @change="chooseFiles"
/>

<br><br>

<div
    v-for="file in uploadedFiles"
    :key="file.id"
    style="
        border:1px solid gray;
        padding:10px;
        margin-bottom:10px;
    "
>
    <div>{{ file.file_type }}</div>

    <img
        v-if="file.file_type === 'image' || file.file_type === 'gif'"
        :src="file.url"
        style="max-width:250px"
    >
    <video
        v-else
        controls
        style="max-width:250px"
    >
        <source :src="file.url">
    </video>

    <br><br>

    <button @click="insertFile(file)">
        Вставить в текст
    </button>
    <button @click="removeUploadedFile(file.id)">
        Удалить
    </button>
</div>

<button :disabled="!canCreate" @click="create">
    {{ editMode ? "Сохранить изменения" : "Опубликовать" }}
</button>

<p>{{ message }}</p>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createPost, updatePost, getPost, searchTags } from "@/api/posts";
import { uploadFiles } from "@/api/upload";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const DRAFTS_KEY = "post_drafts";

const editMode = computed(() => route.path.endsWith("/edit"));
const postId = computed(() => route.params.id as string);

// Генерация или получение существующего ID черновика из query-параметра
const currentDraftId = ref<string>(
    (route.query.draftId as string) || crypto.randomUUID()
);

const title = ref("");
const body = ref("");
const tagInput = ref("");
const foundTags = ref<any[]>([]);
const selectedTags = ref<any[]>([]);
const uploadedFiles = ref<any[]>([]);

let searchTimeout: number | undefined;
const message = ref("");

const canCreate = computed(() => {
    return title.value.trim().length > 0 && body.value.trim().length > 0;
});

function saveDraft() {
    // Сохраняем черновик только если заголовок или текст не пустые
    if (!title.value.trim() && !body.value.trim()) return;

    const drafts = JSON.parse(localStorage.getItem(DRAFTS_KEY) ?? "{}");

    drafts[currentDraftId.value] = {
        id: currentDraftId.value,
        isEditMode: editMode.value,
        originalPostId: postId.value || null,
        title: title.value,
        body: body.value,
        tags: selectedTags.value,
        files: uploadedFiles.value,
        updated_at: Date.now(),
    };

    localStorage.setItem(DRAFTS_KEY, JSON.stringify(drafts));
}

function loadDraft() {
    const drafts = JSON.parse(localStorage.getItem(DRAFTS_KEY) ?? "{}");
    const draft = drafts[currentDraftId.value];

    if (!draft) return;

    title.value = draft.title || "";
    body.value = draft.body || "";
    selectedTags.value = draft.tags || [];
    uploadedFiles.value = draft.files || [];
}

function deleteDraft() {
    const drafts = JSON.parse(localStorage.getItem(DRAFTS_KEY) ?? "{}");
    delete drafts[currentDraftId.value];
    localStorage.setItem(DRAFTS_KEY, JSON.stringify(drafts));
}

async function loadPost() {
    if (!editMode.value) return;

    if (!auth.isAuthenticated) {
        router.replace("/login");
        return;
    }

    try {
        const post = await getPost(postId.value);

        if (auth.user?.id !== post.author_id) {
            router.replace(`/posts/${post.id}`);
            return;
        }

        // Если есть сохранённый черновик редактирования, загружаем его, иначе берем данные с сервера
        const drafts = JSON.parse(localStorage.getItem(DRAFTS_KEY) ?? "{}");
        if (drafts[currentDraftId.value]) {
            loadDraft();
        } else {
            title.value = post.title;
            body.value = post.body;
            selectedTags.value = post.tags.map((tag: any) => ({
                id: tag.id,
                name: tag.name,
            }));
            uploadedFiles.value = post.attachments;
        }
    } catch {
        router.replace("/");
    }
}

async function chooseFiles(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;

    try {
        const files = Array.from(input.files);
        const uploaded = await uploadFiles(files);
        uploadedFiles.value.push(...uploaded);
    } catch (error: any) {
        alert(error.response?.data?.detail ?? "Не удалось загрузить файлы.");
    }

    input.value = "";
}

function insertFile(file: any) {
    body.value += `\n[file:${file.id}]\n`;
}

function removeUploadedFile(id: string) {
    uploadedFiles.value = uploadedFiles.value.filter(file => file.id !== id);
}

async function findTags() {
    if (tagInput.value.trim().length < 3) {
        foundTags.value = [];
        return;
    }

    try {
        foundTags.value = await searchTags(tagInput.value.trim());
    } catch {
        foundTags.value = [];
    }
}

function addExistingTag(tag: any) {
    if (
        selectedTags.value.some(
            t => t.name.trim().toLowerCase() === tag.name.trim().toLowerCase()
        )
    ) {
        return;
    }

    selectedTags.value.push(tag);
    tagInput.value = "";
    foundTags.value = [];
}

function createTag() {
    const name = tagInput.value.trim();
    if (name.length < 3) return;

    const lowerName = name.toLowerCase();

    if (
        selectedTags.value.some(
            tag => tag.name.trim().toLowerCase() === lowerName
        )
    ) {
        return;
    }

    if (
        foundTags.value.some(
            tag => tag.name.trim().toLowerCase() === lowerName
        )
    ) {
        alert("Такой тег уже существует. Выберите его из списка.");
        return;
    }

    selectedTags.value.push({
        id: null,
        name,
    });

    tagInput.value = "";
    foundTags.value = [];
}

function removeTag(index: number) {
    selectedTags.value.splice(index, 1);
}

async function create() {
    message.value = "";

    try {
        const dto = {
            title: title.value,
            body: body.value,
            files_id: uploadedFiles.value.map(file => file.id),
            tags: selectedTags.value,
        };

        let post;
        if (editMode.value) {
            post = await updatePost(postId.value, dto);
        } else {
            post = await createPost(dto);
        }

        deleteDraft();
        router.push(`/posts/${post.id}`);
    } catch (error: any) {
        message.value =
            error.response?.data?.detail ?? "Не удалось сохранить пост.";
    }
}

watch(tagInput, () => {
    clearTimeout(searchTimeout);
    searchTimeout = window.setTimeout(findTags, 300);
});

watch(
    [title, body, selectedTags, uploadedFiles],
    () => {
        saveDraft();
    },
    { deep: true }
);

onMounted(() => {
    if (editMode.value) {
        loadPost();
    } else {
        loadDraft();
    }
});
</script>