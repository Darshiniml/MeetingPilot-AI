import React from 'react';
import { motion } from 'framer-motion';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'danger' | 'ghost' | 'glass';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, variant = 'primary', size = 'md', fullWidth = false, className = '', ...props }, ref) => {
    const baseStyle = "inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:pointer-events-none cursor-pointer";
    
    const variants = {
      primary: "bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-500/20",
      secondary: "bg-zinc-900 text-slate-100 border border-zinc-800 hover:bg-zinc-800",
      accent: "bg-violet-600 text-white hover:bg-violet-500 shadow-lg shadow-violet-500/20",
      danger: "bg-red-600 text-white hover:bg-red-500 shadow-lg shadow-red-500/20",
      ghost: "text-zinc-400 hover:text-slate-100 hover:bg-zinc-800/40",
      glass: "bg-white/5 backdrop-blur-md border border-white/10 text-slate-100 hover:bg-white/10"
    };

    const sizes = {
      sm: "px-3 py-1.5 text-xs",
      md: "px-4 py-2 text-sm",
      lg: "px-6 py-3 text-base"
    };

    const widthStyle = fullWidth ? "w-full" : "";

    return (
      <motion.button
        ref={ref}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.98 }}
        className={`${baseStyle} ${variants[variant]} ${sizes[size]} ${widthStyle} ${className}`}
        {...(props as any)}
      >
        {children}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';
