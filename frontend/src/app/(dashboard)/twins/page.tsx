"use client";

import { useState, useCallback, useRef } from "react";
import { useCustomers, useTwin } from "@/hooks/use-query";
import { TwinVisualization } from "@/components/twins/twin-visualization";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Search, Bot, Download, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

export default function TwinsPage() {
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [compareMode, setCompareMode] = useState(false);
  const [compareCustomerId, setCompareCustomerId] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: customersData } = useCustomers({
    search: search || undefined,
    limit: 50,
  });

  const { data: twin, isLoading: twinLoading } = useTwin(selectedCustomerId || "");
  const { data: compareTwin } = useTwin(compareCustomerId || "");

  const debouncedSearch = useCallback((value: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearch(value);
    }, 300);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Twin Explorer</h1>
          <p className="text-muted-foreground mt-1">
            Explore and analyze customer digital twins
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={compareMode ? "default" : "outline"}
            size="sm"
            onClick={() => setCompareMode(!compareMode)}
          >
            <Bot className="mr-2 h-4 w-4" />
            {compareMode ? "Exit Compare" : "Compare Twins"}
          </Button>
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Customers
            </CardTitle>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search customers..."
                className="pl-9"
                onChange={(e) => debouncedSearch(e.target.value)}
              />
            </div>
          </CardHeader>
          <CardContent className="max-h-[600px] overflow-y-auto space-y-1">
            {customersData?.data?.map((customer) => (
              <button
                key={customer.id}
                onClick={() => setSelectedCustomerId(customer.id)}
                className={cn(
                  "w-full text-left rounded-lg p-3 transition-colors",
                  selectedCustomerId === customer.id
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted"
                )}
              >
                <p className="text-sm font-medium">{customer.name}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {customer.email}
                </p>
              </button>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-6">
          {selectedCustomerId ? (
            twinLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
              </div>
            ) : twin ? (
              <>
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold">
                      {
                        customersData?.data?.find(
                          (c) => c.id === selectedCustomerId
                        )?.name
                      }
                      's Twin
                    </h2>
                  </div>
                  <Button variant="outline" size="sm">
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Rebuild
                  </Button>
                </div>
                <TwinVisualization twin={twin} />
              </>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                No twin data available for this customer.
              </div>
            )
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <Bot className="h-12 w-12 mb-4" />
              <p>Select a customer to view their digital twin</p>
            </div>
          )}

          {compareMode && (
            compareCustomerId && compareTwin ? (
              <div className="border-t pt-6">
                <h3 className="text-lg font-semibold mb-4">Comparison</h3>
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-sm font-medium mb-2">Primary</h4>
                    {twin && <TwinVisualization twin={twin} />}
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium">Comparison</h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setCompareCustomerId(null)}
                      >
                        Change
                      </Button>
                    </div>
                    <TwinVisualization twin={compareTwin} />
                  </div>
                </div>
              </div>
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">
                    Select Comparison Customer
                  </CardTitle>
                </CardHeader>
                <CardContent className="max-h-[400px] overflow-y-auto space-y-1">
                  {customersData?.data?.filter(c => c.id !== selectedCustomerId).map((customer) => (
                    <button
                      key={customer.id}
                      onClick={() => setCompareCustomerId(customer.id)}
                      className={cn(
                        "w-full text-left rounded-lg p-3 transition-colors hover:bg-muted"
                      )}
                    >
                      <p className="text-sm font-medium">{customer.name}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        {customer.email}
                      </p>
                    </button>
                  ))}
                </CardContent>
              </Card>
            )
          )}
        </div>
      </div>
    </div>
  );
}
