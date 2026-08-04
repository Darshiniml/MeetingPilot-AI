import React from 'react';

interface BadgeProps {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info';
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ variant = 'primary', children, className = '' }) => {
  const styles = {
    primary: "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20",
    secondary: "bg-zinc-800 text-zinc-400 border border-zinc-700/50",
    success: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    warning: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
    danger: "bg-red-500/10 text-red-400 border border-red-500/20",
    info: "bg-sky-500/10 text-sky-400 border border-sky-500/20"
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold tracking-wide uppercase ${styles[variant]} ${className}`}>
      {children}
    </span>
  );
};
