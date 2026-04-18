import { timingSafeEqual } from "node:crypto";

import { getConfiguredLoginPassword, hasConfiguredLoginPassword } from "@/lib/auth-config";

export { hasConfiguredLoginPassword };

export function verifyLoginPassword(input: string): boolean {
  const configured = getConfiguredLoginPassword();
  const normalizedInput = input.trim();

  if (!configured || !normalizedInput) {
    return false;
  }

  const configuredBuffer = Buffer.from(configured);
  const inputBuffer = Buffer.from(normalizedInput);

  if (configuredBuffer.length !== inputBuffer.length) {
    return false;
  }

  return timingSafeEqual(configuredBuffer, inputBuffer);
}
