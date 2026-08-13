<template>
  <div class="create-post-container">
    <div class="post-card">
      <h2 class="page-title">
        {{ editMode ? "Редактирование поста" : "Создание поста" }}
      </h2>

      <!-- Основная форма -->
      <div class="form-group">
        <label class="form-label">Заголовок</label>
        <input 
          v-model="title" 
          class="app-input title-input" 
          placeholder="Введите понятный и яркий заголовок..."
        >
      </div>

      <div class="form-group">
        <label class="form-label">Текст поста</label>
        <textarea 
          v-model="body" 
          class="app-textarea" 
          rows="12"
          placeholder="Напишите текст вашего поста..."
        ></textarea>
      </div>

      <!-- Раздел тегов -->
      <div class="form-section">
        <h3 class="section-title">Теги</h3>
        
        <div class="tag-input-wrapper">
          <input 
            v-model="tagInput" 
            class="app-input" 
            placeholder="Поиск или добавление тега..." 
          />

          <!-- Выпадающий список найденных тегов -->
          <div v-if="foundTags.length" class="tags-dropdown">
            <div
              v-for="tag in foundTags"
              :key="tag.id"
              class="tag-dropdown-item"
              @click="addExistingTag(tag)"
            >
              #{{ tag.name }}
            </div>
          </div>
        </div>

        <button 
          v-if="tagInput.trim().length >= 2" 
          class="btn btn-outline btn-create-tag"
          @click="createTag"
        >
          + Создать тег "{{ tagInput }}"
        </button>

        <!-- Список выбранных тегов -->
        <div v-if="selectedTags.length" class="selected-tags-list">
          <span
            v-for="(tag, index) in selectedTags"
            :key="tag.name"
            class="tag-chip"
          >
            #{{ tag.name }}
            <button class="remove-tag-btn" @click="removeTag(index)">×</button>
          </span>
        </div>
      </div>

      <!-- Раздел медиафайлов -->
      <div class="form-section">
        <h3 class="section-title">Медиафайлы</h3>
        
        <label class="file-upload-label">
          <input
            type="file"
            multiple
            accept="image/*,video/*,.gif"
            class="file-input-hidden"
            @change="chooseFiles"
          />
          <svg class="upload-icon" viewBox="0 0 24 24" width="24" height="24">
            <path fill="currentColor" d="M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z"/>
          </svg>
          <span>Нажмите для загрузки медиафайлов</span>
        </label>

        <!-- Сетка превью загруженных файлов -->
        <div v-if="uploadedFiles.length" class="media-grid">
          <div
            v-for="file in uploadedFiles"
            :key="file.id"
            class="media-card"
          >

            <!-- Название файла -->
            <span class="media-name" :title="file.name">
              {{ file.orig_name || file.url }}
            </span>

            <div class="media-actions">
              <button class="btn btn-sm btn-outline" @click="insertFile(file)" title="Вставить ссылку на файл в текст">
                Вставить в текст
              </button>
              <button class="btn btn-sm btn-danger-outline" @click="removeUploadedFile(file.id)">
                Удалить
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Финальное действие -->
      <div class="form-actions">
        <button 
          class="btn btn-primary btn-submit" 
          :disabled="!canCreate" 
          @click="create"
        >
          {{ editMode ? "Сохранить изменения" : "Опубликовать пост" }}
        </button>
        <p v-if="message" class="form-message">{{ message }}</p>
      </div>
    </div>
  </div>
</template>




<script setup lang="ts">
import { computed, ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createPost, updatePost, getPost, searchTags } from "@/api/posts";
import { uploadFiles } from "@/api/upload";
import { useAuthStore } from "@/stores/auth";

import { getCurrentUserId } from "@/api/auth";


const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const userId = getCurrentUserId();
const DRAFTS_KEY = userId ? `post_drafts_${userId}` : "post_drafts_guest";

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

    const MAX_SIZE = 10 * 1024 * 1024; // 10 МБ в байтах
    const files = Array.from(input.files);
    // Проверяем размер каждого файла перед загрузкой
    for (const file of files) {
        if (file.size > MAX_SIZE) {
            alert(`Файл "${file.name}" превышает допустимый размер в 10 МБ.`);
            input.value = "";
            return;
        }
    }

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

    // Удаляем тег файла из тела поста (включая возможные соседние переносы строк)
    const fileTagRegex = new RegExp(`\\n?\\[file:${id}\\]\\n?`, 'g');
    body.value = body.value.replace(fileTagRegex, '');

}

async function findTags() {
    if (tagInput.value.trim().length < 2) {
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
    if (name.length < 2) return;

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



<style scoped>
.create-post-container {
  max-width: 800px;
  margin: 30px auto;
  padding: 0 15px;
}

.post-card {
  background: #ffffff;
  border: 1px solid #eaeaea;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.page-title {
  margin-top: 0;
  margin-bottom: 24px;
  font-size: 24px;
  color: #2c3e50;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.form-label {
  font-weight: 600;
  font-size: 14px;
  color: #2c3e50;
}

.app-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 14px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.title-input {
  font-size: 16px;
  font-weight: 500;
  padding: 12px 14px;
}

.app-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 8px;
  outline: none;
  resize: vertical;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.app-input:focus,
.app-textarea:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.15);
}

/* Form Sections */
.form-section {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #2c3e50;
}

/* Tags */
.tag-input-wrapper {
  position: relative;
  max-width: 400px;
}

.tags-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  max-height: 180px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.tag-dropdown-item {
  padding: 8px 12px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.15s;
}

.tag-dropdown-item:hover {
  background: #f0f7ff;
  color: #1976d2;
}

.btn-create-tag {
  margin-top: 8px;
}

.selected-tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background-color: #f0f7ff;
  color: #1976d2;
  border: 1px solid #d0e3f7;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.remove-tag-btn {
  background: none;
  border: none;
  color: #1976d2;
  font-size: 16px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  display: flex;
  align-items: center;
}

.remove-tag-btn:hover {
  color: #d32f2f;
}

/* File Upload Area */
.file-upload-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  border: 2px dashed #ccc;
  border-radius: 8px;
  background: #fafafa;
  cursor: pointer;
  color: #666;
  font-size: 14px;
  transition: border-color 0.2s, background-color 0.2s;
}

.file-upload-label:hover {
  border-color: #1976d2;
  background: #f0f7ff;
  color: #1976d2;
}

.file-input-hidden {
  display: none;
}

.upload-icon {
  fill: currentColor;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.media-card {
  border: 1px solid #eaeaea;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.media-preview {
  width: 100%;
  height: 140px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.media-preview img,
.media-preview video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.media-actions {
  padding: 10px;
  display: flex;
  gap: 6px;
  justify-content: space-between;
  background: #fff;
  border-top: 1px solid #f0f0f0;
}

/* Submit Actions */
.form-actions {
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.btn-submit {
  width: 100%;
  padding: 12px;
  font-size: 16px;
  font-weight: 600;
}

.form-message {
  margin-top: 12px;
  text-align: center;
  color: #1976d2;
  font-size: 14px;
}

/* Button System */
.btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.btn-sm {
  padding: 6px 10px;
  font-size: 12px;
  border-radius: 6px;
}

.btn-primary {
  background-color: #1976d2;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1565c0;
}

.btn-primary:disabled {
  background-color: #90caf9;
  cursor: not-allowed;
}

.btn-outline {
  background-color: transparent;
  border-color: #1976d2;
  color: #1976d2;
}

.btn-outline:hover {
  background-color: #f0f7ff;
}

.btn-danger-outline {
  background-color: transparent;
  border-color: #ffcdd2;
  color: #d32f2f;
}

.btn-danger-outline:hover {
  background-color: #ffebee;
}
</style>