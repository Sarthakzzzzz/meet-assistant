import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getBackendUrl() {
  const envUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (envUrl && !envUrl.includes("undefined")) {
    return envUrl;
  }
  return typeof window !== "undefined" ? `${window.location.protocol}//${window.location.hostname}:8000` : "http://localhost:8000";
}

export function getWsUrl() {
  const envUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (envUrl && !envUrl.includes("undefined")) {
    return envUrl;
  }
  return typeof window !== "undefined" ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.hostname}:8000` : "ws://localhost:8000";
}
