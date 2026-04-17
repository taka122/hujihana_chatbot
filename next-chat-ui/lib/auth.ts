"use client";

const CLINIC_KEY_STORAGE = "hujihana_clinic_key";

function getClinicKeyStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage;
}

function clearLegacyClinicKey(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(CLINIC_KEY_STORAGE);
  }
}

export function saveClinicKey(key: string) {
  const storage = getClinicKeyStorage();
  if (storage) {
    clearLegacyClinicKey();
    storage.setItem(CLINIC_KEY_STORAGE, key);
  }
}

export function getClinicKey(): string | null {
  const storage = getClinicKeyStorage();
  if (storage) {
    clearLegacyClinicKey();
    return storage.getItem(CLINIC_KEY_STORAGE);
  }
  return null;
}

export function clearClinicKey() {
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(CLINIC_KEY_STORAGE);
    window.localStorage.removeItem(CLINIC_KEY_STORAGE);
  }
}

export function isAuthenticated(): boolean {
  return !!getClinicKey();
}
