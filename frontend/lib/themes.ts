export type ThemeKey = "light" | "dark" | "td" | "comfort";

export interface Theme {
  name: string;
  bg: string;
  surface: string;
  surface2: string;
  border: string;
  accent: string;
  accentLight: string;
  text: string;
  muted: string;
  faint: string;
  // Chrome bar (browser top bar)
  chromeBg: string;
  chromeText: string;
}

export const THEMES: Record<ThemeKey, Theme> = {
  light: {
    name: "Light",
    bg: "#ffffff",
    surface: "#f8fafc",
    surface2: "#f1f5f9",
    border: "#e2e8f0",
    accent: "#0f4c8a",
    accentLight: "#e8f0fa",
    text: "#0f172a",
    muted: "#64748b",
    faint: "#94a3b8",
    chromeBg: "#f1f5f9",
    chromeText: "#94a3b8",
  },
  dark: {
    name: "Dark",
    bg: "#0f172a",
    surface: "#1e293b",
    surface2: "#334155",
    border: "#334155",
    accent: "#60a5fa",
    accentLight: "#1e3a5f",
    text: "#f1f5f9",
    muted: "#94a3b8",
    faint: "#64748b",
    chromeBg: "#1e293b",
    chromeText: "#64748b",
  },
  td: {
    name: "TD",
    bg: "#f4f6f4",
    surface: "#ffffff",
    surface2: "#e8f0e8",
    border: "#d1e0d1",
    accent: "#00a650",
    accentLight: "#e6f7ee",
    text: "#0f1f0f",
    muted: "#4a6741",
    faint: "#7a9e72",
    chromeBg: "#e8f0e8",
    chromeText: "#7a9e72",
  },
  comfort: {
    name: "Comfort",
    bg: "#1d1d1d",
    surface: "#2a2a2a",
    surface2: "#333333",
    border: "rgba(255,255,255,0.12)",
    accent: "#a78bfa",
    accentLight: "#a78bfa33",
    text: "#ffffff",
    muted: "#999999",
    faint: "#666666",
    chromeBg: "#2a2a2a",
    chromeText: "#666666",
  },
};

export const THEME_KEYS: ThemeKey[] = ["light", "dark", "td", "comfort"];
