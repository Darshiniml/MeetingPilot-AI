import React from 'react';

interface SkeletonProps {
  variant?: 'text' | 'rect' | 'circle';
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ variant = 'rect', className = '' }) => {
  const styles = {
    text: "h-3 w-3/4 rounded",
    rect: "h-12 w-full rounded-lg",
    circle: "h-10 w-10 rounded-full"
  };

  return (
    <div className={`shimmer bg-zinc-800/50 ${styles[variant]} ${className}`} />
  );
};
