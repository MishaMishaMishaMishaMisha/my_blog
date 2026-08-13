<template>
  <div class="editor-container">
    <textarea
      v-model="text"
      maxlength="2000"
      placeholder="Написать комментарий..."
      class="editor-textarea"
    ></textarea>

    <div v-if="files.length" class="files-preview-list">
      <div v-for="(file, index) in files" :key="file.id" class="file-chip">
        <span class="file-url">{{ file.orig_name || file.url }}</span>
        <button type="button" class="btn-remove-file" @click="removeFile(index)" title="Удалить файл">×</button>
      </div>
    </div>

    <div class="editor-toolbar">
      <div class="editor-attachments">
        <button type="button" class="btn-attach" @click="selectFiles">
          📎 Добавить медиафайл
        </button>
      </div>

      <div class="editor-actions">
        <button 
          v-if="parentId || isEditing" 
          type="button" 
          class="btn btn-outline btn-sm"
          @click="$emit('cancel')"
        >
          Отмена
        </button>
        <button 
          type="button" 
          class="btn btn-primary btn-sm"
          :disabled="sending || !isChanged" 
          @click="send"
        >
          {{ sending ? 'Сохранение...' : (isEditing ? 'Сохранить' : 'Отправить') }}
        </button>
      </div>
    </div>
  </div>
</template>




<script setup lang="ts">
import { ref, computed } from "vue";
import { uploadFiles } from "@/api/upload";
import { addComment, updateComment } from "@/api/comments";
import type { Comment, CreatedCommentResponse, Attachment } from "@/api/comments";

const props = defineProps<{
  postId: string;
  parentId?: string | null;
  // Если начальный комментарий передан — редактор работает в режиме "Редактирование"
  initialComment?: Comment | null; 
}>();

const emit = defineEmits<{
  created: [comment: Comment];
  updated: [comment: Comment];
  cancel: [];
}>();

const isEditing = computed(() => !!props.initialComment);

// Заполняем начальными данными, если редактируем
const text = ref(props.initialComment?.body ?? "");
const files = ref<Attachment[]>(props.initialComment?.attachments ? [...props.initialComment.attachments] : []);
const sending = ref(false);

// Проверка: изменились ли данные по сравнению с исходным комментарием
const isChanged = computed(() => {

  const hasContent = text.value.trim().length > 0 || files.value.length > 0;

  if (!isEditing.value) return hasContent;
  
  const initialText = props.initialComment?.body ?? "";
  const initialFilesIds = (props.initialComment?.attachments ?? []).map(f => f.id).sort().join(",");
  const currentFilesIds = files.value.map(f => f.id).sort().join(",");

  return text.value.trim() !== initialText || currentFilesIds !== initialFilesIds;
});

async function removeFile(index: number) {
  files.value.splice(index, 1);
}

async function selectFiles() {
  const input = document.createElement("input");
  input.type = "file";
  input.multiple = true;
  input.accept = "image/*,video/*";

  input.onchange = async () => {
    const selected = Array.from(input.files ?? []);

    if (files.value.length + selected.length > 1) {
      alert("Максимум 1 файл.");
      return;
    }

    const MAX_SIZE = 10 * 1024 * 1024; // 10 МБ в байтах
    for (const file of selected) {
        if (file.size > MAX_SIZE) {
            alert(`Файл "${file.name}" превышает допустимый размер в 10 МБ.`);
            input.value = "";
            return;
        }
    }


    try {
      const uploaded = await uploadFiles(selected);
      files.value.push(...uploaded);
    } catch (error: any) {
        alert(error.response?.data?.detail ?? "Не удалось загрузить файлы.");
    }
  };

  input.click();
}

async function send() {
  
  const hasContent = text.value.trim().length > 0 || files.value.length > 0;
  if (!isChanged.value || !hasContent) return;

  sending.value = true;

  try {
    if (isEditing.value && props.initialComment) {
      // Режим обновления
      const updated = await updateComment(props.initialComment.id, {
        body: text.value,
        files_id: files.value.map((f) => f.id),
      });
      emit("updated", updated);
    } else {
      // Режим создания
      const createdData: CreatedCommentResponse = await addComment(props.postId, {
        parent_id: props.parentId ?? null,
        body: text.value,
        files_id: files.value.map((x) => x.id),
      });

      const fullComment: Comment = {
        ...createdData,
        attachments: files.value,
        reactions: { like: 0, dislike: 0, fire: 0, shit: 0, laugh: 0 },
        count_replies: 0,
        user_reaction: null,
      };

      text.value = "";
      files.value = [];
      emit("created", fullComment);
    }
  } catch (e: any) {
    if (error.response?.status !== 403) {
      alert(e.response?.data?.detail ?? "Ошибка при сохранении.");
    }
  } finally {
    sending.value = false;
  }
}
</script>



<style scoped>
.editor-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 12px;
  margin-top: 12px;
}

.editor-textarea {
  width: 100%;
  box-sizing: border-box;
  min-height: 70px;
  padding: 10px;
  font-size: 14px;
  font-family: inherit;
  border: 1px solid #ccc;
  border-radius: 6px;
  outline: none;
  resize: vertical;
  background: #ffffff;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.editor-textarea:focus {
  border-color: #1976d2;
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.12);
}

.files-preview-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.file-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #eef4fc;
  border: 1px solid #d0e3f7;
  border-radius: 4px;
  font-size: 12px;
  color: #1976d2;
  max-width: 100%;
}

.file-url {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.btn-remove-file {
  background: none;
  border: none;
  color: #1976d2;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.btn-remove-file:hover {
  color: #d32f2f;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.editor-attachments {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-attach {
  background: none;
  border: 1px solid #ccc;
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: #555;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-attach:hover {
  background: #f0f0f0;
}

.file-count {
  font-size: 12px;
  color: #888;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

/* Button System */
.btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
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
  border-color: #ccc;
  color: #555;
}

.btn-outline:hover {
  background-color: #f0f0f0;
}
</style>