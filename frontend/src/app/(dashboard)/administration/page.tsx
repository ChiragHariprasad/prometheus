"use client";

import { useState } from "react";
import { useAuditLogs, useSystemHealth, useFeatureFlags } from "@/hooks/use-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Shield,
  Activity,
  Flag,
  Clock,
  Gauge,
  Search,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Play,
  Pause,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

export default function AdministrationPage() {
  const [activeTab, setActiveTab] = useState("audit");
  const [auditFilters, setAuditFilters] = useState({
    action: "",
    user_id: "",
    resource: "",
    start_date: "",
    end_date: "",
  });

  const { data: auditLogs } = useAuditLogs({
    ...(auditFilters.action && { action: auditFilters.action }),
    ...(auditFilters.user_id && { user_id: auditFilters.user_id }),
  });

  const { data: systemHealth } = useSystemHealth();
  const { data: featureFlags } = useFeatureFlags();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Administration</h1>
        <p className="text-muted-foreground mt-1">
          System management and monitoring
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full justify-start border-b rounded-none h-auto p-0 bg-transparent overflow-x-auto">
          {[
            { id: "audit", label: "Audit Log", icon: Shield },
            { id: "health", label: "System Health", icon: Activity },
            { id: "features", label: "Feature Flags", icon: Flag },
            { id: "jobs", label: "Background Jobs", icon: Clock },
            { id: "rate-limits", label: "Rate Limits", icon: Gauge },
          ].map((tab) => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 py-2 gap-2"
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="audit" className="mt-6 space-y-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-wrap gap-4 items-end">
                <div className="space-y-2">
                  <Label>Action</Label>
                  <Select
                    value={auditFilters.action}
                    onValueChange={(v) =>
                      setAuditFilters((prev) => ({ ...prev, action: v }))
                    }
                  >
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="All actions" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All</SelectItem>
                      <SelectItem value="login">Login</SelectItem>
                      <SelectItem value="create">Create</SelectItem>
                      <SelectItem value="update">Update</SelectItem>
                      <SelectItem value="delete">Delete</SelectItem>
                      <SelectItem value="export">Export</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Resource</Label>
                  <Input
                    placeholder="Resource type"
                    className="w-40"
                    value={auditFilters.resource}
                    onChange={(e) =>
                      setAuditFilters((prev) => ({
                        ...prev,
                        resource: e.target.value,
                      }))
                    }
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={() =>
                    setAuditFilters({
                      action: "",
                      user_id: "",
                      resource: "",
                      start_date: "",
                      end_date: "",
                    })
                  }
                >
                  Clear Filters
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Resource</TableHead>
                    <TableHead>Details</TableHead>
                    <TableHead>IP Address</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditLogs?.data?.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="text-xs">
                        {format(new Date(log.timestamp), "MMM d, HH:mm:ss")}
                      </TableCell>
                      <TableCell className="font-medium text-xs">
                        {log.user_name}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-[10px]">
                          {log.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">{log.resource}</TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">
                        {JSON.stringify(log.details)}
                      </TableCell>
                      <TableCell className="text-xs font-mono">
                        {log.ip_address}
                      </TableCell>
                    </TableRow>
                  ))}
                  {(!auditLogs?.data || auditLogs.data.length === 0) && (
                    <TableRow>
                      <TableCell
                        colSpan={6}
                        className="h-24 text-center text-muted-foreground"
                      >
                        No audit logs found.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="health" className="mt-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Recent Errors
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-destructive">
                  {systemHealth?.recent_errors || 0}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Avg Response Time
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {systemHealth?.avg_response_time || 0}ms
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Requests/Min
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {systemHealth?.requests_per_minute || 0}
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Service Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {systemHealth?.services?.map((service) => (
                <div
                  key={service.name}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-2">
                    {service.status === "healthy" ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : service.status === "degraded" ? (
                      <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )}
                    <span className="font-medium text-sm">{service.name}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{service.latency}ms</span>
                    <span>{service.uptime.toFixed(2)}% uptime</span>
                    <Badge
                      variant={
                        service.status === "healthy"
                          ? "success"
                          : service.status === "degraded"
                            ? "warning"
                            : "destructive"
                      }
                    >
                      {service.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="features" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Feature Flags
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {featureFlags?.map((flag) => (
                <div
                  key={flag.key}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div>
                    <p className="font-medium text-sm">{flag.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {flag.description}
                    </p>
                    <code className="text-xs text-muted-foreground mt-1 block">
                      {flag.key}
                    </code>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={flag.enabled}
                      onChange={() => {}}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary" />
                  </label>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="jobs" className="mt-6">
          <Card>
            <CardContent className="space-y-3 pt-6">
              {[
                { name: "Twin Rebuild", status: "running", progress: 65 },
                { name: "Segment Computation", status: "completed", progress: 100 },
                { name: "Campaign Dispatch", status: "queued", progress: 0 },
                { name: "Data Export", status: "failed", progress: 45 },
              ].map((job) => (
                <div
                  key={job.name}
                  className="rounded-lg border p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm">{job.name}</span>
                    <Badge
                      variant={
                        job.status === "completed"
                          ? "success"
                          : job.status === "running"
                            ? "default"
                            : job.status === "failed"
                              ? "destructive"
                              : "secondary"
                      }
                    >
                      {job.status}
                    </Badge>
                  </div>
                  <Progress value={job.progress} className="h-2" />
                  <p className="text-xs text-muted-foreground mt-1">
                    {job.progress}% complete
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rate-limits" className="mt-6">
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Endpoint</TableHead>
                    <TableHead>Limit</TableHead>
                    <TableHead>Remaining</TableHead>
                    <TableHead>Resets At</TableHead>
                    <TableHead>Usage</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[
                    { endpoint: "/api/customers", limit: 1000, remaining: 723, reset: "15 min" },
                    { endpoint: "/api/events/ingest", limit: 5000, remaining: 4120, reset: "5 min" },
                    { endpoint: "/api/twins", limit: 500, remaining: 234, reset: "1 hour" },
                    { endpoint: "/api/campaigns", limit: 200, remaining: 145, reset: "1 hour" },
                  ].map((rate) => (
                    <TableRow key={rate.endpoint}>
                      <TableCell className="font-mono text-xs">
                        {rate.endpoint}
                      </TableCell>
                      <TableCell>{rate.limit.toLocaleString()}</TableCell>
                      <TableCell>{rate.remaining.toLocaleString()}</TableCell>
                      <TableCell className="text-xs">{rate.reset}</TableCell>
                      <TableCell>
                        <Progress
                          value={
                            ((rate.limit - rate.remaining) / rate.limit) * 100
                          }
                          className="w-24 h-2"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
