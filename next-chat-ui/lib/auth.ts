"use client";

const CLINIC_KEY_STORAGE = "hujihana_clinic_key";

export function saveClinicKey(key: str) {
  if (typeof window !== "undefined") {
    localStorage.setItem(CLINIC_KEY_STORAGE, key);
  }
}

export function getClinicKey(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem(CLINIC_KEY_STORAGE);
  }
  return null;
}

export function clearClinicKey() {
  if (typeof window !== "undefined") {
    localStorage.removeItem(CLINIC_KEY_STORAGE);
  }
}

export function isAuthenticated(): boolean {
  return !!getClinicKey();
}
