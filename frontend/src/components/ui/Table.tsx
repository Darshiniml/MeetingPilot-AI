import React from 'react';

interface Column<T> {
  header: string;
  accessor: keyof T | ((row: T) => React.ReactNode);
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  className?: string;
}

export function Table<T>({ columns, data, onRowClick, className = '' }: TableProps<T>) {
  return (
    <div className={`w-full overflow-x-auto border border-zinc-800 rounded-xl bg-zinc-900/40 ${className}`}>
      <table className="w-full border-collapse text-left text-sm text-zinc-300">
        <thead className="bg-zinc-950/80 border-b border-zinc-800 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          <tr>
            {columns.map((col, idx) => (
              <th key={idx} className={`px-6 py-4 ${col.className || ''}`}>{col.header}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/60">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-6 py-10 text-center text-zinc-500">
                No data available
              </td>
            </tr>
          ) : (
            data.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                onClick={() => onRowClick?.(row)}
                className={`transition-colors duration-150 ${onRowClick ? 'hover:bg-zinc-800/30 cursor-pointer' : 'hover:bg-zinc-800/10'}`}
              >
                {columns.map((col, colIdx) => {
                  const content = typeof col.accessor === 'function'
                    ? col.accessor(row)
                    : (row[col.accessor] as React.ReactNode);
                  return (
                    <td key={colIdx} className={`px-6 py-4 whitespace-nowrap ${col.className || ''}`}>
                      {content}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
