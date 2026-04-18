export function getConfiguredLoginPassword(): string {
  return (process.env.CLINIC_PASSWORD ?? process.env.LOGIN_PASSWORD ?? "").trim();
}

export function hasConfiguredLoginPassword(): boolean {
  return getConfiguredLoginPassword().length > 0;
}
