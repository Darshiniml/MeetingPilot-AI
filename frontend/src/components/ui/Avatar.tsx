import React from 'react';

interface AvatarProps {
  name?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({ name = '?', size = 'md', className = '' }) => {
  const sizes = {
    sm: "w-7 h-7 text-xs",
    md: "w-9 h-9 text-sm",
    lg: "w-12 h-12 text-base"
  };

  const getInitials = (str: string) => {
    const parts = str.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + (parts[1] ? parts[1][0] : '')).toUpperCase();
    }
    return str.slice(0, 2).toUpperCase();
  };

  const getGradient = (str: string) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const idx = Math.abs(hash % 5);
    const gradients = [
      "from-indigo-600 to-violet-500",
      "from-violet-600 to-fuchsia-500",
      "from-emerald-600 to-teal-500",
      "from-blue-600 to-sky-500",
      "from-rose-600 to-pink-500"
    ];
    return gradients[idx];
  };

  return (
    <div className={`flex items-center justify-center rounded-full font-bold text-white bg-gradient-to-br ${getGradient(name)} select-none shrink-0 ${sizes[size]} ${className}`}>
      {getInitials(name)}
    </div>
  );
};
