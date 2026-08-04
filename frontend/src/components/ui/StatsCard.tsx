import React from 'react';
import { Card } from './Card';
import type { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  title: string;
  value: string | number;
  trend?: string;
  trendType?: 'up' | 'down' | 'neutral';
  icon: LucideIcon;
  className?: string;
}

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  trend,
  trendType = 'neutral',
  icon: Icon,
  className = ''
}) => {
  const trendColors = {
    up: "text-emerald-400 bg-emerald-500/10",
    down: "text-red-400 bg-red-500/10",
    neutral: "text-zinc-400 bg-zinc-800"
  };

  return (
    <Card hoverEffect={true} className={`flex items-center justify-between p-6 ${className}`}>
      <div className="flex flex-col text-left">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">{title}</span>
        <span className="text-2xl font-bold text-slate-100 mb-2">{value}</span>
        {trend && (
          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold w-fit ${trendColors[trendType]}`}>
            {trend}
          </span>
        )}
      </div>
      <div className="w-12 h-12 rounded-lg bg-zinc-950 flex items-center justify-center text-indigo-400 border border-zinc-800/80">
        <Icon size={20} className="stroke-[1.8]" />
      </div>
    </Card>
  );
};
