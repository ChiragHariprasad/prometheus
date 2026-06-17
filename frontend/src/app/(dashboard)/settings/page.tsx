"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import {
  Settings,
  Users,
  Shield,
  Key,
  CreditCard,
  Lock,
  Save,
  Plus,
  Trash2,
  Copy,
} from "lucide-react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Manage your organization settings and preferences
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full justify-start border-b rounded-none h-auto p-0 bg-transparent overflow-x-auto">
          {[
            { id: "general", label: "General", icon: Settings },
            { id: "users", label: "Users", icon: Users },
            { id: "roles", label: "Roles", icon: Shield },
            { id: "integrations", label: "Integrations", icon: Key },
            { id: "billing", label: "Billing", icon: CreditCard },
            { id: "security", label: "Security", icon: Lock },
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

        <TabsContent value="general" className="mt-6 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Organization Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Organization Name</Label>
                  <Input defaultValue="Acme Corp" />
                </div>
                <div className="space-y-2">
                  <Label>Industry</Label>
                  <Select defaultValue="technology">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="technology">Technology</SelectItem>
                      <SelectItem value="retail">Retail</SelectItem>
                      <SelectItem value="finance">Finance</SelectItem>
                      <SelectItem value="healthcare">Healthcare</SelectItem>
                      <SelectItem value="education">Education</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Website</Label>
                <Input defaultValue="https://acme-corp.com" />
              </div>
              <Button>
                <Save className="mr-2 h-4 w-4" />
                Save Changes
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="users" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">
                  User Management
                </CardTitle>
                <Button size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Invite User
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[
                    { name: "John Doe", email: "john@acme.com", role: "Admin", status: "Active" },
                    { name: "Jane Smith", email: "jane@acme.com", role: "Editor", status: "Active" },
                    { name: "Bob Wilson", email: "bob@acme.com", role: "Viewer", status: "Inactive" },
                  ].map((user) => (
                    <TableRow key={user.email}>
                      <TableCell className="font-medium">{user.name}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{user.role}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={user.status === "Active" ? "success" : "secondary"}>
                          {user.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roles" className="mt-6">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              Role and permission management interface.
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="integrations" className="mt-6 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">
                  API Keys
                </CardTitle>
                <Button size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Generate Key
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Key</TableHead>
                    <TableHead>Permissions</TableHead>
                    <TableHead>Last Used</TableHead>
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[
                    { name: "Production API", key: "tcx_live_••••••••", permissions: "Read, Write", lastUsed: "2 min ago" },
                    { name: "Dev API", key: "tcx_test_••••••••", permissions: "Read", lastUsed: "1 hour ago" },
                  ].map((key) => (
                    <TableRow key={key.name}>
                      <TableCell className="font-medium">{key.name}</TableCell>
                      <TableCell>
                        <code className="rounded bg-muted px-2 py-1 text-xs">
                          {key.key}
                        </code>
                      </TableCell>
                      <TableCell>{key.permissions}</TableCell>
                      <TableCell className="text-xs">{key.lastUsed}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">
                  Webhooks
                </CardTitle>
                <Button size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Webhook
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { name: "Customer Sync", url: "https://api.acme.com/webhooks/prometheus", events: "customer.created, customer.updated", active: true },
                { name: "Campaign Events", url: "https://api.acme.com/webhooks/campaigns", events: "campaign.launched, campaign.completed", active: true },
              ].map((webhook) => (
                <div key={webhook.name} className="rounded-lg border p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{webhook.name}</span>
                    <Badge variant={webhook.active ? "success" : "secondary"}>
                      {webhook.active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono mb-1">{webhook.url}</p>
                  <p className="text-xs text-muted-foreground">Events: {webhook.events}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="billing" className="mt-6">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              Billing and usage information.
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="mt-6 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Password & Authentication
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Current Password</Label>
                <Input type="password" />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>New Password</Label>
                  <Input type="password" />
                </div>
                <div className="space-y-2">
                  <Label>Confirm Password</Label>
                  <Input type="password" />
                </div>
              </div>
              <Button>Update Password</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Multi-Factor Authentication
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div>
                  <p className="font-medium">MFA Status</p>
                  <p className="text-sm text-muted-foreground">
                    Add an extra layer of security to your account
                  </p>
                </div>
                <Button variant="outline">Enable MFA</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Single Sign-On (SSO)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div>
                  <p className="font-medium">SAML/SSO Configuration</p>
                  <p className="text-sm text-muted-foreground">
                    Configure SAML-based single sign-on
                  </p>
                </div>
                <Button variant="outline">Configure</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
