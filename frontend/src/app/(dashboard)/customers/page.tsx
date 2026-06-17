"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCustomers } from "@/hooks/use-query";
import { CustomerTable } from "@/components/customers/customer-table";
import { StatsCard } from "@/components/dashboard/stats-card";
import { Button } from "@/components/ui/button";
import { Users, UserPlus, Download, Filter } from "lucide-react";

export default function CustomersPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [sortField, setSortField] = useState("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useCustomers({
    page,
    limit: 20,
    sort: sortField,
    order: sortOrder,
    search: search || undefined,
  });

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Customers</h1>
          <p className="text-muted-foreground mt-1">
            Manage and analyze your customer base
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button onClick={() => router.push("/customers/new")}>
            <UserPlus className="mr-2 h-4 w-4" />
            Add Customer
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          label="Total Customers"
          value={data?.total?.toLocaleString() || "—"}
          icon={<Users className="h-4 w-4 text-white" />}
          color="bg-blue-500"
        />
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
        </div>
      ) : (
        <CustomerTable
          customers={data?.data || []}
          total={data?.total || 0}
          page={page}
          pageSize={20}
          onPageChange={setPage}
          onSort={handleSort}
          sortField={sortField}
          sortOrder={sortOrder}
          onSearch={(q) => {
            setSearch(q);
            setPage(1);
          }}
        />
      )}
    </div>
  );
}
