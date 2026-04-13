import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

export function extractPageNumber(ref: string): number | null {
  const patterns = [/p\.?\s*(\d+)/i, /page\s*(\d+)/i, /slide\s*(\d+)/i];
  for (const pattern of patterns) {
    const match = ref.match(pattern);
    if (match) {
      return Number(match[1]);
    }
  }
  return null;
}

export function withPageAnchor(url: string, page: number | null): string {
  if (!page) {
    return url;
  }
  if (url.includes("#")) {
    return `${url}&page=${page}`;
  }
  return `${url}#page=${page}`;
}

export function extractTimestamp(ref: string): number | null {
  const match = ref.match(/(\d{1,2}):(\d{2})/);
  if (match) {
    const mins = parseInt(match[1], 10);
    const secs = parseInt(match[2], 10);
    return mins * 60 + secs;
  }
  return null;
}

export function isGoogleDriveUrl(url?: string | null): boolean {
  return typeof url === "string" && url.includes("drive.google.com");
}

export function toDownloadUrl(url: string): string {
  try {
    if (!isGoogleDriveUrl(url)) {
      return url;
    }

    const parsed = new URL(url);
    const fileIdFromPath = parsed.pathname.match(/\/file\/d\/([^/]+)/)?.[1];
    const fileIdFromQuery = parsed.searchParams.get("id");
    const fileId = fileIdFromPath ?? fileIdFromQuery;

    if (!fileId) {
      return url;
    }

    return `https://drive.google.com/uc?export=download&id=${encodeURIComponent(fileId)}`;
  } catch {
    return url;
  }
}
