<template>
  <div class="editor">
    <textarea
      v-model="text"
      maxlength="2000"
      placeholder="Написать комментарий..."
    />

    <div class="editor-actions">
      <button type="button" @click="selectFiles">Добавить файлы</button>
      <span>{{ files.length }}/3</span>
    </div>

    <div v-for="(file, index) in files" :key="file.id" class="file-preview">
    <span>{{ file.url }}</span>
    <button type="button" @click="removeFile(index)">❌</button>
    </div>

    <div class="buttons">

        <button type="button" @click="send" :disabled="sending || !isChanged">
            {{ sending ? 'Сохранение...' : (isEditing ? 'Сохранить' : 'Отправить') }}
        </button>
        <button v-if="parentId || isEditing" type="button" @click="$emit('cancel')">
            Отмена
        </button>

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
  if (!isEditing.value) return text.value.trim().length > 0;
  
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

    if (files.value.length + selected.length > 3) {
      alert("Максимум 3 файла.");
      return;
    }

    try {
      const uploaded = await uploadFiles(selected);
      files.value.push(...uploaded);
    } catch {
      alert("Ошибка загрузки файлов.");
    }
  };

  input.click();
}

async function send() {
  if (!isChanged.value || text.value.trim().length === 0) return;

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
    alert(e.response?.data?.detail ?? "Ошибка при сохранении.");
  } finally {
    sending.value = false;
  }
}
</script>



<style scoped>
.editor {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
textarea {
  width: 100%;
  min-height: 60px;
}
.buttons {
  display: flex;
  gap: 8px;
}
</style>