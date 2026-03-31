from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class GeminiApiError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self, api_key: str, base_url: str = "https://generativelanguage.googleapis.com/v1beta") -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def embed_query(self, model: str, query: str) -> list[float]:
        payload = {
            "model": f"models/{model}",
            "taskType": "RETRIEVAL_QUERY",
            "content": {"parts": [{"text": query}]},
        }
        data = self._post(f"models/{model}:embedContent", payload)
        vector = data.get("embedding", {}).get("values", [])
        if not vector:
            raise GeminiApiError("Gemini query embedding is empty")
        return [float(v) for v in vector]

    def embed_documents(self, model: str, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        requests: list[dict[str, Any]] = []
        for index, text in enumerate(texts):
            requests.append(
                {
                    "model": f"models/{model}",
                    "taskType": "RETRIEVAL_DOCUMENT",
                    "title": f"chunk-{index}",
                    "content": {"parts": [{"text": text}]},
                }
            )

        payload = {"requests": requests}
        data = self._post(f"models/{model}:batchEmbedContents", payload)
        embeddings = data.get("embeddings", [])
        if len(embeddings) != len(texts):
            raise GeminiApiError(
                f"Gemini embedding count mismatch: expected={len(texts)} got={len(embeddings)}"
            )
        return [[float(v) for v in item.get("values", [])] for item in embeddings]

    def generate_content(
        self,
        model: str,
        system_instruction: str,
        user_prompt: str,
        file_uri: str | None = None,
        mime_type: str | None = None,
    ) -> str:
        parts: list[dict[str, Any]] = [{"text": user_prompt}]
        if file_uri and mime_type:
            parts.insert(0, {"file_data": {"mime_type": mime_type, "file_uri": file_uri}})

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.0},
        }
        data = self._post(f"models/{model}:generateContent", payload)
        for candidate in data.get("candidates", []):
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if text and text.strip():
                    return text.strip()
        raise GeminiApiError("Gemini returned no text candidates")

    def extract_text_from_images(
        self,
        model: str,
        images: list[tuple[str, bytes]],
        prompt: str = "画像から読み取れるテキストをそのまま抽出し、不要な説明を付けずに返してください。",
    ) -> str:
        if not images:
            return ""

        parts: list[dict[str, Any]] = [{"text": prompt}]
        for mime_type, raw_bytes in images:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64.b64encode(raw_bytes).decode("ascii"),
                    }
                }
            )

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.0},
        }
        data = self._post(f"models/{model}:generateContent", payload)
        for candidate in data.get("candidates", []):
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if text and text.strip():
                    return text.strip()
        raise GeminiApiError("Gemini OCR returned no text candidates")

    def upload_file(self, content: bytes, mime_type: str, display_name: str) -> dict[str, Any]:
        """Uploads a file to Gemini File API (v1beta)."""
        url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={self._api_key}"
        
        # Simple upload format for simplicity, though resumable is recommended for large files.
        # For this PoC, we use the non-resumable simple upload if possible.
        # If it needs metadata, we should use resumable. 
        # Here we do a two-step resumable-like approach or just provide metadata in headers.
        
        metadata = {"file": {"display_name": display_name}}
        body = json.dumps(metadata).encode("utf-8")
        
        # 1. Initiate upload
        init_request = urllib.request.Request(
            url=url,
            method="POST",
            data=body,
            headers={
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "start",
                "X-Goog-Upload-Header-Content-Length": str(len(content)),
                "X-Goog-Upload-Header-Content-Type": mime_type,
                "Content-Type": "application/json",
            },
        )
        
        try:
            with urllib.request.urlopen(init_request) as resp:
                upload_url = resp.headers.get("X-Goog-Upload-URL")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise GeminiApiError(f"Gemini File Init Error {exc.code}: {body}") from exc

        if not upload_url:
            raise GeminiApiError("Failed to get upload URL from Gemini")

        # 2. Upload actual data
        data_request = urllib.request.Request(
            url=upload_url,
            method="POST",
            data=content,
            headers={
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "upload, finalize",
                "X-Goog-Upload-Offset": "0",
                "Content-Length": str(len(content)),
            },
        )
        
        try:
            with urllib.request.urlopen(data_request) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw).get("file", {})
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise GeminiApiError(f"Gemini File Upload Error {exc.code}: {body}") from exc

    def get_file_status(self, name: str) -> dict[str, Any]:
        """Gets file status (e.g. processing state). name format is 'files/...'"""
        data = self._post(name, payload={}, method="GET")
        return data

    def _post(self, path: str, payload: dict[str, Any], method: str = "POST") -> dict[str, Any]:
        url = f"{self._base_url}/{path}"
        data_bytes = json.dumps(payload).encode("utf-8") if payload else None
        request = urllib.request.Request(
            url=url,
            method=method,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise GeminiApiError(f"Gemini API HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise GeminiApiError(f"Gemini API connection error: {exc}") from exc

        parsed = json.loads(raw)
        if "error" in parsed:
            raise GeminiApiError(str(parsed["error"]))
        return parsed
