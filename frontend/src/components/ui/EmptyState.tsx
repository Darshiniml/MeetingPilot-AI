import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { Button } from './Button';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className = ''
}) => {
  return (
    <div className={`flex flex-col items-center justify-center text-center p-8 border border-dashed border-zinc-800 rounded-xl bg-zinc-950/20 max-w-lg mx-auto ${className}`}>
      <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 mb-4 shrink-0">
        <Icon size={22} className="stroke-[1.5]" />
      </div>
      <h3 className="text-base font-bold text-slate-100 mb-1.5">{title}</h3>
      <p className="text-sm text-zinc-400 mb-6 max-w-sm">{description}</p>
      {actionLabel && onAction && (
        <Button variant="secondary" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
