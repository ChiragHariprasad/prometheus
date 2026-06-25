import React from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-zinc-200 dark:border-zinc-800 mb-6">
      <div className="flex flex-col gap-0.5">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground font-sans">{title}</h1>
        {subtitle && (
          <p className="text-sm text-muted-foreground font-sans">{subtitle}</p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2 mt-3 sm:mt-0">
          {actions}
        </div>
      )}
    </div>
  );
}
export default PageHeader;
