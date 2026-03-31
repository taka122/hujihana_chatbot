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

    def embed_query(self, model: str, query: str, output_dimensionality: int | None = None) -> list[float]:
        payload: dict[str, Any] = {
            "model": f"models/{model}",
            "taskType": "RETRIEVAL_QUERY",
            "content": {"parts": [{"text": query}]},
        }
        if output_dimensionality is not None:
            payload["outputDimensionality"] = output_dimensionality
        data = self._post(f"models/{model}:embedContent", payload)
        vector = data.get("embedding", {}).get("values", [])
        if not vector:
            raise GeminiApiError("Gemini query embedding is empty")
        return [float(v) for v in vector]

    def embed_documents(self, model: str, texts: list[str], output_dimensionality: int | None = None) -> list[list[float]]:
        if not texts:
            return []
        requests: list[dict[str, Any]] = []
        for index, text in enumerate(texts):
            req: dict[str, Any] = {
                "model": f"models/{model}",
                "taskType": "RETRIEVAL_DOCUMENT",
                "title": f"chunk-{index}",
                "content": {"parts": [{"text": text}]},
            }
            if output_dimensionality is not None:
                req["outputDimensionality"] = output_dimensionality
            requests.append(req)

        payload = {"requests": requests}
        data = self._post(f"models/{model}:batchEmbedContents", payload)
        embeddings = data.get("embeddings", [])
        if len(embeddings) != len(texts):
            raise GeminiApiError(
                f"Gemini embedding count mismatch: expected={len(texts)} got={len(embeddings)}"
            )
        return [[float(v) for v in item.get("values", [])] for item in embeddings]

    def generate_content(self, model: str, system_instruction: str, user_prompt: str) -> str:
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
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

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/{path}"
        request = urllib.request.Request(
            url=url,
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
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
