import { useState, useEffect, useCallback } from 'react';

type Theme = 'light' | 'dark' | 'system';

function getSystemTheme(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function getResolved(theme: Theme): 'light' | 'dark' {
  return theme === 'system' ? getSystemTheme() : theme;
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark' || saved === 'system') return saved;
    return 'system';
  });

  const [resolved, setResolved] = useState<'light' | 'dark'>(() => getResolved(theme));

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    localStorage.setItem('theme', t);
  }, []);

  // 切换 <html> 的 dark 类
  useEffect(() => {
    const r = getResolved(theme);
    setResolved(r);
    document.documentElement.classList.toggle('dark', r === 'dark');
  }, [theme]);

  // 监听系统主题变化
  useEffect(() => {
    if (theme !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      const r = getSystemTheme();
      setResolved(r);
      document.documentElement.classList.toggle('dark', r === 'dark');
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [theme]);

  // 循环切换: system → light → dark → system
  const toggleTheme = useCallback(() => {
    const next: Theme = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system';
    setTheme(next);
  }, [theme, setTheme]);

  return { theme, resolved, setTheme, toggleTheme };
}
