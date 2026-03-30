"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchIngestionReport } from "@/lib/api/client";
import type { IngestionReport } from "@/lib/api/types";

export function useIngestionReport(workspaceId: string, docId: string, enabled = true) {
  return useQuery<IngestionReport>({
    queryKey: ["ingestion-report", workspaceId, docId],
    queryFn: () => fetchIngestionReport(workspaceId, docId),
    enabled: enabled && Boolean(workspaceId) && Boolean(docId)
  });
}
