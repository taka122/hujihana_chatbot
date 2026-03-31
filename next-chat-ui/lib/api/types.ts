export type Workspace = {
  id: string;
  name: string;
};

export type CreateWorkspaceRequest = {
  name: string;
};

export type UploadResponse = {
  doc_id: string;
};

export type DocStatus = "processing" | "ready" | "failed";

export type Doc = {
  doc_id: string;
  file_name: string;
  mime: string;
  status: DocStatus;
  page_count: number | null;
  tags: string[];
  updated_at: string;
  fail_reason: string | null;
};

export type Citation = {
  doc_id: string;
  file_name: string;
  ref_type: "page" | "slide" | "sheet" | "video";
  ref: string;
  snippet: string;
  score: number | null;
  chunk_id?: string;
  mime_type?: string;
};

export type ChatAnswer = {
  conclusion: string;
  details: string;
  notes: string;
  next_actions: string[];
};

export type ChatResponse = {
  answer: ChatAnswer;
  citations: Citation[];
};

export type ChatRequest = {
  query: string;
};

export type IngestionReport = {
  doc_id: string;
  extracted_pages: number;
  failed_pages: Array<{ page: number; reason: string }>;
  ocr_used_pages: number[];
  chunk_count: number;
  estimated_cost: number | null;
};

export type SourcePreview = {
  url?: string;
  snippet?: string;
  text?: string;
  [key: string]: unknown;
};

export type ApiErrorBody = {
  message?: string;
  error?: string;
  detail?: string;
};
