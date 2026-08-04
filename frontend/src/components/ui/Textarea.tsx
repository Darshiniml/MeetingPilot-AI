import React from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="w-full flex flex-col gap-1.5 text-left">
        {label && <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{label}</label>}
        <textarea
          ref={ref}
          className={`w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3.5 py-2 text-sm text-slate-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all min-h-[90px] ${className}`}
          {...props}
        />
        {error && <span className="text-xs font-medium text-red-500">{error}</span>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
