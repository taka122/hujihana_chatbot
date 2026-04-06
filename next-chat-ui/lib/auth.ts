const CLINIC_KEY_STORAGE = "hujihana_clinic_key";

export const AUTH_COOKIE_NAME = "fujihana-chat-auth";
export const AUTH_COOKIE_VALUE = "authenticated";

export function saveClinicKey(key: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(CLINIC_KEY_STORAGE, key);
  }
}

export function getClinicKey(): string | null {
  if (typeof window !== "undefined") {
    return window.localStorage.getItem(CLINIC_KEY_STORAGE);
  }
  return null;
}

export function clearClinicKey(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(CLINIC_KEY_STORAGE);
  }
}

export function isAuthenticated(): boolean {
  return !!getClinicKey();
}

export function hasConfiguredLoginPassword(): boolean {
  return typeof process.env.APP_LOGIN_PASSWORD === "string" && process.env.APP_LOGIN_PASSWORD.trim().length > 0;
}

export function verifyLoginPassword(input: string): boolean {
  const candidate = input.trim();
  if (!candidate) {
    return false;
  }

  const configured = process.env.APP_LOGIN_PASSWORD?.trim();
  if (!configured) {
    return true;
  }

  return candidate === configured;
}
