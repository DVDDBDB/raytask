// Theme context: light | dark | system. Persists per-user.
import React, { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext(null);

const apply = (mode) => {
  const root = document.documentElement;
  const effective =
    mode === "system"
      ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : mode;
  if (effective === "dark") root.classList.add("dark");
  else root.classList.remove("dark");
};

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem("raybotix_theme") || "system");

  useEffect(() => {
    apply(theme);
    localStorage.setItem("raybotix_theme", theme);
    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      const handler = () => apply("system");
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
