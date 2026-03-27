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
