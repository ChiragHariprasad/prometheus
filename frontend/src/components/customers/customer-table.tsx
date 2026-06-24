"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Customer } from "@/lib/api-client";
import { formatDistanceToNow } from "date-fns";
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  Eye,
  MoreHorizontal,
  Search,
  ArrowUpDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface CustomerTableProps {
  customers: Customer[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onSort: (field: string) => void;
  sortField?: string;
  sortOrder?: "asc" | "desc";
  onSearch?: (query: string) => void;
  onSelectionChange?: (ids: string[]) => void;
}

type SortableField = "name" | "email" | "engagement_score" | "loyalty_score" | "churn_risk" | "ltv" | "last_activity";

export function CustomerTable({
  customers,
  total,
  page,
  pageSize,
  onPageChange,
  onSort,
  sortField,
  sortOrder,
  onSearch,
}: CustomerTableProps) {
  const router = useRouter();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const totalPages = Math.ceil(total / pageSize);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === customers.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(customers.map((c) => c.id));
    }
  };

  const SortHeader = ({
    field,
    children,
  }: {
    field: SortableField;
    children: React.ReactNode;
  }) => {
    const isActive = sortField === field;
    return (
      <TableHead
        className="cursor-pointer select-none"
        onClick={() => onSort(field)}
      >
        <div className="flex items-center gap-1">
          {children}
          {isActive ? (
            sortOrder === "asc" ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )
          ) : (
            <ChevronsUpDown className="h-4 w-4 opacity-30" />
          )}
        </div>
      </TableHead>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search customers..."
            className="pl-9"
            onChange={(e) => onSearch?.(e.target.value)}
          />
        </div>
        <Select defaultValue="all">
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Engagement" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
        <Select defaultValue="all">
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Churn Risk" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <input
                  type="checkbox"
                  checked={
                    customers.length > 0 &&
                    selectedIds.length === customers.length
                  }
                  onChange={toggleSelectAll}
                  className="h-4 w-4"
                />
              </TableHead>
              <SortHeader field="name">Name</SortHeader>
              <SortHeader field="email">Email</SortHeader>
              <SortHeader field="engagement_score">Engagement</SortHeader>
              <SortHeader field="loyalty_score">Loyalty</SortHeader>
              <SortHeader field="churn_risk">Churn Risk</SortHeader>
              <SortHeader field="ltv">LTV</SortHeader>
              <SortHeader field="last_activity">Last Seen</SortHeader>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.map((customer) => (
              <TableRow
                key={customer.id}
                className="cursor-pointer"
                onClick={() => router.push(`/customers/${customer.id}`)}
              >
                <TableCell
                  onClick={(e) => e.stopPropagation()}
                  className="w-10"
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(customer.id)}
                    onChange={() => toggleSelect(customer.id)}
                    className="h-4 w-4"
                  />
                </TableCell>
                <TableCell className="font-medium">{customer.name}</TableCell>
                <TableCell className="text-muted-foreground">
                  {customer.email}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Progress
                      value={customer.engagement_score}
                      className={cn(
                        "w-16 h-2",
                        customer.engagement_score >= 70
                          ? "[&>div]:bg-engagement-high"
                          : customer.engagement_score >= 40
                            ? "[&>div]:bg-engagement-medium"
                            : "[&>div]:bg-engagement-low"
                      )}
                    />
                    <span className="text-xs text-muted-foreground">
                      {customer.engagement_score}%
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Progress
                      value={customer.loyalty_score}
                      className="w-16 h-2 [&>div]:bg-primary"
                    />
                    <span className="text-xs text-muted-foreground">
                      {customer.loyalty_score}%
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={
                      customer.churn_risk === "high"
                        ? "destructive"
                        : customer.churn_risk === "medium"
                          ? "warning"
                          : "success"
                    }
                  >
                    {customer.churn_risk}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono">
                  ${customer.ltv.toLocaleString()}
                </TableCell>
                <TableCell className="text-muted-foreground text-xs">
                  {customer.last_activity
                    ? formatDistanceToNow(new Date(customer.last_activity), {
                        addSuffix: true,
                      })
                    : "No activity"}
                </TableCell>
                <TableCell
                  onClick={(e) => e.stopPropagation()}
                  className="w-10"
                >
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Actions</DropdownMenuLabel>
                      <DropdownMenuItem
                        onClick={() =>
                          router.push(`/customers/${customer.id}`)
                        }
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        View Profile
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem>Add to Segment</DropdownMenuItem>
                      <DropdownMenuItem>Send Campaign</DropdownMenuItem>
                      <DropdownMenuItem>Export Data</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
            {customers.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={9}
                  className="h-24 text-center text-muted-foreground"
                >
                  No customers found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Showing {(page - 1) * pageSize + 1}-
          {Math.min(page * pageSize, total)} of {total}
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
