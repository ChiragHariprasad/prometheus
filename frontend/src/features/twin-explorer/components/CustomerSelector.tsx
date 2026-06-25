import React, { useState, useEffect, useRef } from 'react';
import { useCustomers } from '../../../hooks/queries';
import { Customer } from '../../../types';
import { Search, Loader2, ChevronDown, Check, User } from 'lucide-react';
import { cn } from '../../../utils';

interface CustomerSelectorProps {
  selectedId?: string;
  onSelect: (customer: Customer) => void;
}

export function CustomerSelector({ selectedId, onSelect }: CustomerSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Debounce search term to minimize query triggers
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const { data: customersData, isLoading } = useCustomers(1, 10, debouncedSearch);
  const customers: Customer[] = customersData?.data || [];

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedCustomer = customers.find(c => c.id === selectedId);

  return (
    <div className="relative w-full max-w-sm font-sans" ref={dropdownRef}>
      {/* Dropdown Trigger */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full h-10 px-3 rounded border border-zinc-200 dark:border-zinc-800 bg-card hover:border-zinc-400 dark:hover:border-zinc-700 flex items-center justify-between text-left text-sm transition-colors"
      >
        {selectedCustomer ? (
          <div className="flex items-center gap-2 truncate">
            <div className="h-6 w-6 rounded-full bg-accent/10 text-accent flex items-center justify-center text-xs font-semibold">
              {selectedCustomer.first_name?.charAt(0) || selectedCustomer.email?.charAt(0)?.toUpperCase() || '?'}
            </div>
            <div className="truncate">
              <span className="font-semibold text-foreground">
                {selectedCustomer.first_name ? `${selectedCustomer.first_name} ${selectedCustomer.last_name}` : selectedCustomer.email}
              </span>
            </div>
          </div>
        ) : (
          <span className="text-muted-foreground">Select customer twin...</span>
        )}
        <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0 ml-2" />
      </button>

      {/* Dropdown Options */}
      {isOpen && (
        <div className="absolute left-0 mt-1 w-full max-w-sm rounded-md border border-zinc-200 dark:border-zinc-800 bg-card shadow-lg z-50 overflow-hidden">
          {/* Search Input */}
          <div className="flex items-center border-b px-3 h-10 bg-zinc-50 dark:bg-zinc-900/30">
            <Search className="h-4 w-4 text-muted-foreground mr-2 shrink-0" />
            <input
              type="text"
              placeholder="Search customers..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-transparent text-sm focus:outline-none text-foreground placeholder:text-muted-foreground"
            />
            {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground shrink-0" />}
          </div>

          {/* List */}
          <ul className="max-h-60 overflow-y-auto divide-y divide-zinc-100 dark:divide-zinc-900">
            {customers.length === 0 ? (
              <li className="px-4 py-3 text-xs text-muted-foreground text-center">
                No matching customers found.
              </li>
            ) : (
              customers.map((c) => {
                const active = c.id === selectedId;
                const displayName = c.first_name ? `${c.first_name} ${c.last_name}` : (c.email || 'Unknown');
                return (
                  <li
                    key={c.id}
                    onClick={() => {
                      onSelect(c);
                      setIsOpen(false);
                      setSearchTerm('');
                    }}
                    className={cn(
                      "px-4 py-2 text-xs flex items-center justify-between cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900/30",
                      active && "bg-accent/5 dark:bg-accent/10"
                    )}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <div className="h-5 w-5 rounded-full bg-zinc-100 dark:bg-zinc-850 flex items-center justify-center text-[10px] font-bold text-muted-foreground">
                        {displayName.charAt(0).toUpperCase()}
                      </div>
                      <div className="truncate">
                        <p className="font-semibold text-foreground truncate">{displayName}</p>
                        <p className="text-[10px] text-muted-foreground truncate">{c.email}</p>
                      </div>
                    </div>
                    {active && <Check className="h-3.5 w-3.5 text-accent shrink-0 ml-2" />}
                  </li>
                );
              })
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
export default CustomerSelector;
