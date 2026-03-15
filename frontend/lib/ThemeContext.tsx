"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { type ThemeKey, THEMES } from "./themes";

interface ThemeContextValue {
  theme: ThemeKey;
  setTheme: (t: ThemeKey) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "light",
  setTheme: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeKey>("light");

  useEffect(() => {
    const saved = (localStorage.getItem("theme") as ThemeKey) || "light";
    if (saved in THEMES) {
      setThemeState(saved);
      document.documentElement.dataset.theme = saved;
    }
  }, []);

  function setTheme(t: ThemeKey) {
    setThemeState(t);
    localStorage.setItem("theme", t);
    document.documentElement.dataset.theme = t;
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
