import React from 'react';
import { cn } from '../../utils';

interface Column<T> {
  header: string;
  accessor: (item: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  data?: T[];
  columns: Column<T>[];
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
  rowClassName?: (item: T) => string;
}

export function DataTable<T>({
  data = [],
  columns,
  loading = false,
  emptyMessage = 'No data available.',
  onRowClick,
  rowClassName,
}: DataTableProps<T>) {
  return (
    <div className="relative w-full overflow-auto rounded-md border border-zinc-200 dark:border-zinc-800 bg-card">
      <table className="w-full caption-bottom text-sm">
        <thead className="bg-zinc-100 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
          <tr className="transition-colors">
            {columns.map((column, idx) => (
              <th
                key={idx}
                className={cn(
                  "h-10 px-4 text-left align-middle text-xs font-semibold text-muted-foreground uppercase tracking-wider",
                  column.className
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {loading ? (
            Array.from({ length: 5 }).map((_, rIdx) => (
              <tr key={rIdx} className="h-12 animate-pulse">
                {columns.map((_, cIdx) => (
                  <td key={cIdx} className="px-4 py-3 align-middle">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr className="h-24">
              <td colSpan={columns.length} className="px-4 py-8 text-center text-sm text-muted-foreground">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((item, idx) => (
              <tr
                key={idx}
                onClick={() => onRowClick?.(item)}
                className={cn(
                  "transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900/50",
                  onRowClick && "cursor-pointer",
                  rowClassName?.(item)
                )}
              >
                {columns.map((column, cIdx) => (
                  <td key={cIdx} className={cn("px-4 py-3 align-middle text-foreground", column.className)}>
                    {column.accessor(item)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
export default DataTable;
