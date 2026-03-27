"use client";

import { useMutation } from "@tanstack/react-query";

import { queryChat } from "@/lib/api/client";

export function useChat(workspaceId: string) {
  return useMutation({
    mutationFn: (query: string) => queryChat(workspaceId, { query })
  });
}
