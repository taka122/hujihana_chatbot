"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiKeySettingsFab } from "@/components/api-key-settings-fab";
import { Toaster } from "@/components/ui/toaster";

export function AppProviders({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false
          }
        }
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ApiKeySettingsFab />
      <Toaster />
    </QueryClientProvider>
  );
}
