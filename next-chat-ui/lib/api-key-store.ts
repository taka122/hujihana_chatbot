"use client";

const API_KEY_STORAGE_KEY = "universal-rag-api-key";

function isIso88591(value: string): boolean {
  for (const char of value) {
    if (char.charCodeAt(0) > 0xff) {
      return false;
    }
  }
  return true;
}

function normalizeApiKey(value: string): string {
  return value.replace(/[\r\n]+/g, "").trim();
}

export function isApiKeyHeaderSafe(value: string): boolean {
  const normalized = normalizeApiKey(value);
  return normalized.length > 0 && isIso88591(normalized);
}

export function getStoredApiKey(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const value = window.localStorage.getItem(API_KEY_STORAGE_KEY);
  if (!value) {
    return null;
  }
  const normalized = normalizeApiKey(value);
  if (normalized.length === 0) {
    window.localStorage.removeItem(API_KEY_STORAGE_KEY);
    return null;
  }
  if (!isIso88591(normalized)) {
    window.localStorage.removeItem(API_KEY_STORAGE_KEY);
    return null;
  }
  return normalized;
}

export function saveApiKey(value: string): void {
  if (typeof window === "undefined") {
    return;
  }
  const normalized = normalizeApiKey(value);
  if (!normalized) {
    window.localStorage.removeItem(API_KEY_STORAGE_KEY);
    return;
  }
  if (!isIso88591(normalized)) {
    window.localStorage.removeItem(API_KEY_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(API_KEY_STORAGE_KEY, normalized);
}

export function clearApiKey(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(API_KEY_STORAGE_KEY);
}
