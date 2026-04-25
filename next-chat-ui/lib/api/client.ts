import type {
  ApiErrorBody,
  ChatRequest,
  ChatResponse,
  CreateWorkspaceRequest,
  Doc,
  IngestionReport,
  SourcePreview,
  UploadResponse,
  Workspace
} from "@/lib/api/types";

import { getStoredApiKey } from "@/lib/api-key-store";

const API_PROXY_PREFIX = "/api/backend";

type JsonRecord = Record<string, unknown>;

function asRecord(value: unknown): JsonRecord | undefined {
  if (typeof value === "object" && value !== null) {
    return value as JsonRecord;
  }
  return undefined;
}

function resolveUrl(path: string): string {
  if (!path.startsWith("/")) {
    return path;
  }
  return `${API_PROXY_PREFIX}${path}`;
}

function getApiKeyHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};

  const apiKey = getStoredApiKey();
  if (apiKey) {
    headers["X-GEMINI-API-Key"] = apiKey;
  }

  return headers;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (await response.text()) as T;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const apiHeaders = getApiKeyHeaders();
  let response: Response;
  try {
    response = await fetch(resolveUrl(path), {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...apiHeaders,
        ...(init?.headers ?? {})
      },
      cache: "no-store"
    });
  } catch (error) {
    if (
      error instanceof Error &&
      error.message.toLowerCase().includes("non iso-8859-1")
    ) {
      throw new Error(
        "リクエストヘッダに使えない文字が含まれています。Gemini API KEY設定を削除または再入力してください。"
      );
    }
    throw new Error(
      error instanceof Error
        ? `${error.message} (API接続に失敗しました。Nextプロキシ設定またはバックエンド起動状態を確認してください)`
        : "API接続に失敗しました。Nextプロキシ設定またはバックエンド起動状態を確認してください。"
    );
  }

  if (!response.ok) {
    const payload = (await parseResponse<ApiErrorBody | string>(response)) ?? "";
    let message =
      typeof payload === "string"
        ? payload
        : payload.error ?? payload.message ?? payload.detail ?? `Request failed (${response.status})`;
    throw new Error(message);
  }

  return parseResponse<T>(response);
}

function normalizeWorkspace(raw: unknown): Workspace {
  const item = asRecord(raw);
  const id = String(item?.id ?? "");
  const name = String(item?.name ?? "");
  return { id, name };
}

function normalizeDoc(raw: unknown): Doc {
  const item = asRecord(raw);
  const statusRaw = String(item?.status ?? "failed").toLowerCase();
  const status: Doc["status"] =
    statusRaw === "ready" || statusRaw === "processing" || statusRaw === "failed"
      ? statusRaw
      : "failed";

  return {
    doc_id: String(item?.doc_id ?? item?.id ?? ""),
    file_name: String(item?.file_name ?? ""),
    mime: String(item?.mime ?? item?.mime_type ?? ""),
    status,
    page_count: typeof item?.page_count === "number" ? item.page_count : null,
    tags: Array.isArray(item?.tags) ? item.tags.map((tag) => String(tag)) : [],
    updated_at: String(item?.updated_at ?? item?.created_at ?? new Date().toISOString()),
    fail_reason:
      item?.fail_reason == null || item.fail_reason === "" ? null : String(item.fail_reason)
  };
}

function normalizeIngestionReport(raw: unknown): IngestionReport {
  const item = asRecord(raw);
  return {
    doc_id: String(item?.doc_id ?? item?.document_id ?? ""),
    extracted_pages: typeof item?.extracted_pages === "number" ? item.extracted_pages : 0,
    failed_pages: Array.isArray(item?.failed_pages)
      ? item.failed_pages
          .map((value) => {
            const failed = asRecord(value);
            const page = typeof failed?.page === "number" ? failed.page : Number(failed?.page ?? NaN);
            const reason = String(failed?.reason ?? "");
            if (!Number.isFinite(page) || !reason) {
              return null;
            }
            return { page, reason };
          })
          .filter((value): value is { page: number; reason: string } => value !== null)
      : [],
    ocr_used_pages: Array.isArray(item?.ocr_used_pages)
      ? item.ocr_used_pages
          .map((value) => (typeof value === "number" ? value : Number(value)))
          .filter((value) => Number.isFinite(value))
      : [],
    chunk_count: typeof item?.chunk_count === "number" ? item.chunk_count : 0,
    estimated_cost: typeof item?.estimated_cost === "number" ? item.estimated_cost : null
  };
}

function normalizeChatResponse(raw: unknown): ChatResponse {
  const payload = asRecord(raw);
  const answer = asRecord(payload?.answer);
  const citations = Array.isArray(payload?.citations) ? payload.citations : [];
  const normalizedCitations = citations
    .map((value) => {
      const citation = asRecord(value);
      const docId = citation?.doc_id;
      const fileName = citation?.file_name;
      const refType = citation?.ref_type;
      const ref = citation?.ref;
      const snippet = citation?.snippet;
      const normalizedRefType: "page" | "slide" | "sheet" | null =
        refType === "page" || refType === "slide" || refType === "sheet" ? refType : null;
      if (
        (typeof docId !== "string" && typeof docId !== "number") ||
        (typeof fileName !== "string" && typeof fileName !== "number") ||
        !normalizedRefType ||
        (typeof ref !== "string" && typeof ref !== "number") ||
        (typeof snippet !== "string" && typeof snippet !== "number")
      ) {
        return null;
      }
        return {
          doc_id: String(docId),
          file_name: String(fileName),
          ref_type: normalizedRefType,
          ref: String(ref),
          snippet: String(snippet),
        score: typeof citation?.score === "number" ? citation.score : null,
        chunk_id: citation?.chunk_id == null ? undefined : String(citation.chunk_id)
      };
    })
    .filter((value): value is NonNullable<typeof value> => value !== null);

  const clarificationRaw = asRecord(payload?.clarification);
  const clarification = clarificationRaw
    ? {
        needed: Boolean(clarificationRaw.needed),
        question: String(clarificationRaw.question ?? ""),
        options: Array.isArray(clarificationRaw.options)
          ? clarificationRaw.options
              .map((value) => String(value).trim())
              .filter((value) => value.length > 0)
          : []
      }
    : null;

  return {
    answer: {
      conclusion: String(answer?.conclusion ?? ""),
      details: String(answer?.details ?? ""),
      notes: String(answer?.notes ?? ""),
      next_actions: Array.isArray(answer?.next_actions)
        ? answer.next_actions.map((value) => String(value))
        : []
    },
    citations: normalizedCitations,
    clarification: clarification && clarification.needed ? clarification : null
  };
}

export async function fetchWorkspaces(): Promise<Workspace[]> {
  const payload = await request<unknown>("/api/workspaces");
  const items = Array.isArray(payload) ? payload : [];
  return items.map((item) => normalizeWorkspace(item)).filter((item) => item.id.length > 0);
}

export async function createWorkspace(body: CreateWorkspaceRequest): Promise<Workspace> {
  const payload = await request<unknown>("/api/workspaces", {
    method: "POST",
    body: JSON.stringify(body)
  });
  return normalizeWorkspace(payload);
}

export async function deleteWorkspace(workspaceId: string): Promise<void> {
  await request<unknown>(`/api/workspaces/${workspaceId}`, {
    method: "DELETE"
  });
}

export async function fetchDocs(workspaceId: string): Promise<Doc[]> {
  const payload = await request<unknown>(`/api/workspaces/${workspaceId}/docs`);
  const items = Array.isArray(payload) ? payload : [];
  return items.map((item) => normalizeDoc(item)).filter((item) => item.doc_id.length > 0);
}

export async function fetchDoc(workspaceId: string, docId: string): Promise<Doc> {
  const payload = await request<unknown>(`/api/workspaces/${workspaceId}/docs/${docId}`);
  return normalizeDoc(payload);
}

export async function deleteDoc(workspaceId: string, docId: string): Promise<void> {
  await request<unknown>(`/api/workspaces/${workspaceId}/docs/${docId}`, {
    method: "DELETE"
  });
}

export async function uploadDoc(
  workspaceId: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<UploadResponse> {
  const apiKeyHeaders = getApiKeyHeaders();
  return new Promise<UploadResponse>((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", resolveUrl(`/api/workspaces/${workspaceId}/docs/upload`));
    Object.entries(apiKeyHeaders).forEach(([header, value]) => {
      xhr.setRequestHeader(header, value);
    });

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable || !onProgress) {
        return;
      }
      onProgress(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onload = () => {
      try {
        const payload = JSON.parse(xhr.responseText) as unknown;
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(payload as UploadResponse);
          return;
        }
        const errorBody =
          typeof payload === "object" && payload !== null ? (payload as ApiErrorBody) : undefined;
        reject(new Error(errorBody?.error ?? errorBody?.message ?? "Upload failed"));
      } catch {
        reject(new Error(xhr.responseText || "Upload failed"));
      }
    };

    xhr.onerror = () => {
      reject(new Error("アップロードに失敗しました。ネットワーク状態を確認してください。"));
    };

    xhr.send(formData);
  });
}

export async function fetchIngestionReport(
  workspaceId: string,
  docId: string
): Promise<IngestionReport> {
  const payload = await request<unknown>(`/api/workspaces/${workspaceId}/docs/${docId}/ingestion-report`);
  return normalizeIngestionReport(payload);
}

export async function fetchDocPresignedUrl(workspaceId: string, docId: string): Promise<string> {
  const payload = await request<unknown>(`/api/workspaces/${workspaceId}/docs/${docId}/presigned-url`);
  const item = asRecord(payload);
  if (!item || typeof item.url !== "string" || item.url.length === 0) {
    throw new Error("プレビューURLの取得に失敗しました。");
  }
  return item.url;
}

export async function queryChat(
  workspaceId: string,
  body: ChatRequest
): Promise<ChatResponse> {
  const payload = await request<unknown>(`/api/workspaces/${workspaceId}/chat/query`, {
    method: "POST",
    body: JSON.stringify(body)
  });
  return normalizeChatResponse(payload);
}

export async function fetchSourcePreview(
  workspaceId: string,
  docId: string,
  ref: string
): Promise<SourcePreview> {
  const encodedRef = encodeURIComponent(ref);
  const authHeaders = getApiKeyHeaders();
  let response = await fetch(resolveUrl(`/api/workspaces/${workspaceId}/docs/${docId}/preview?ref=${encodedRef}`), {
    headers: authHeaders,
    cache: "no-store"
  });

  if (response.status === 404) {
    // Backend compatibility fallback: use presigned URL endpoint when preview endpoint is absent.
    response = await fetch(resolveUrl(`/api/workspaces/${workspaceId}/docs/${docId}/presigned-url`), {
      headers: authHeaders,
      cache: "no-store"
    });
  }

  if (!response.ok) {
    const payload = (await parseResponse<ApiErrorBody | string>(response)) ?? "";
    const message =
      typeof payload === "string"
        ? payload
        : payload.error ?? payload.message ?? payload.detail ?? "Preview failed";
    throw new Error(message);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const payload = (await response.json()) as SourcePreview | string;
    if (typeof payload === "string") {
      return { url: payload };
    }
    return {
      url: typeof payload.url === "string" ? payload.url : undefined,
      snippet: typeof payload.snippet === "string" ? payload.snippet : undefined,
      text: typeof payload.text === "string" ? payload.text : undefined,
      ...payload
    };
  }

  const text = await response.text();
  if (/^https?:\/\//i.test(text.trim())) {
    return { url: text.trim() };
  }
  return { text };
}
