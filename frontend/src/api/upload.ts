import api from "./axios";

export async function uploadFiles(files: File[]) {

    const form = new FormData();

    for (const file of files) {
        form.append("files", file);
    }

    const response = await api.post(
        "/upload/multiple",
        form,
    );

    return response.data;

}

export async function uploadFile(file: File) {

    const form = new FormData();

    form.append("file", file);

    const response = await api.post(
        "/upload/one-file",
        form,
    );

    return response.data;

}