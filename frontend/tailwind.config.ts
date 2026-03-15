import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#ffffff",
        surface: "#f8fafc",
        surface2: "#f1f5f9",
        border: "#e2e8f0",
        accent: "#0f4c8a",
        "accent-light": "#e8f0fa",
        red: { DEFAULT: "#dc2626", light: "#fef2f2" },
        green: { DEFAULT: "#059669", light: "#ecfdf5" },
        yellow: { DEFAULT: "#d97706", light: "#fffbeb" },
        purple: { DEFAULT: "#7c3aed", light: "#f5f3ff" },
        text: "#0f172a",
        muted: "#64748b",
        faint: "#94a3b8",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      borderRadius: {
        tag: "4px",
        btn: "8px",
        card: "12px",
        "card-lg": "16px",
      },
      boxShadow: {
        card: "0 20px 50px rgba(0,0,0,0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
