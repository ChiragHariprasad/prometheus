"use client";

import { useState } from "react";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useSegments, useCreateCampaign } from "@/hooks/use-query";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  Mail,
  MessageSquare,
  Bell,
  Smartphone,
} from "lucide-react";

const STEPS = [
  { id: "basic", title: "Basic Info" },
  { id: "targeting", title: "Targeting" },
  { id: "content", title: "Content" },
  { id: "schedule", title: "Schedule" },
  { id: "abtest", title: "A/B Test" },
  { id: "review", title: "Review & Launch" },
];

export function CampaignBuilder() {
  const router = useRouter();
  const { data: segments } = useSegments();
  const createCampaign = useCreateCampaign();
  const [currentStep, setCurrentStep] = useState(0);
  const [form, setForm] = useState({
    name: "",
    type: "email" as "email" | "sms" | "push" | "in_app",
    goal: "",
    segment_ids: [] as string[],
    content: { subject: "", body: "" },
    schedule: { start: new Date().toISOString().slice(0, 16), timezone: Intl.DateTimeFormat().resolvedOptions().timeZone },
    ab_test: { enabled: false, variants: [] as { name: string; content: { subject: string; body: string }; traffic_percentage: number }[], winning_metric: "open_rate" },
  });

  const update = (field: string, value: unknown) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0:
        return !!form.name && !!form.goal;
      case 1:
        return form.segment_ids.length > 0;
      case 2:
        return !!form.content.subject && !!form.content.body;
      case 3:
        return !!form.schedule.start;
      default:
        return true;
    }
  };

  const handleSubmit = async () => {
    const campaignData = {
      name: form.name,
      type: form.type,
      channel: form.type,
      goal: form.goal,
      segments: form.segment_ids,
      content: form.content,
      schedule: {
        start: new Date(form.schedule.start).toISOString(),
        timezone: form.schedule.timezone,
      },
      ab_test_config: form.ab_test.enabled ? form.ab_test : undefined,
    };

    try {
      const result = await createCampaign.mutateAsync(campaignData);
      router.push(`/campaigns/${result.id}`);
    } catch {
      // handle error
    }
  };

  return (
    <div className="space-y-8">
      {/* Steps indicator */}
      <div className="flex items-center gap-2">
        {STEPS.map((step, i) => (
          <div key={step.id} className="flex items-center gap-2">
            <button
              onClick={() => i < currentStep && setCurrentStep(i)}
              className={cn(
                "flex items-center gap-2 rounded-full px-3 py-1 text-sm transition-colors",
                i === currentStep
                  ? "bg-primary text-primary-foreground"
                  : i < currentStep
                    ? "bg-primary/10 text-primary hover:bg-primary/20"
                    : "bg-muted text-muted-foreground"
              )}
            >
              {i < currentStep ? (
                <Check className="h-3 w-3" />
              ) : (
                <span>{i + 1}</span>
              )}
              <span className="hidden sm:inline">{step.title}</span>
            </button>
            {i < STEPS.length - 1 && (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{STEPS[currentStep].title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Step 1: Basic Info */}
          {currentStep === 0 && (
            <>
              <div className="space-y-2">
                <Label htmlFor="name">Campaign Name</Label>
                <Input
                  id="name"
                  value={form.name}
                  onChange={(e) => update("name", e.target.value)}
                  placeholder="e.g., Summer Sale 2025"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="type">Channel</Label>
                <Select
                  value={form.type}
                  onValueChange={(v) => update("type", v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="email">
                      <span className="flex items-center gap-2">
                        <Mail className="h-4 w-4" /> Email
                      </span>
                    </SelectItem>
                    <SelectItem value="sms">
                      <span className="flex items-center gap-2">
                        <MessageSquare className="h-4 w-4" /> SMS
                      </span>
                    </SelectItem>
                    <SelectItem value="push">
                      <span className="flex items-center gap-2">
                        <Bell className="h-4 w-4" /> Push
                      </span>
                    </SelectItem>
                    <SelectItem value="in_app">
                      <span className="flex items-center gap-2">
                        <Smartphone className="h-4 w-4" /> In-App
                      </span>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="goal">Goal</Label>
                <Input
                  id="goal"
                  value={form.goal}
                  onChange={(e) => update("goal", e.target.value)}
                  placeholder="e.g., Increase Q2 revenue by 15%"
                />
              </div>
            </>
          )}

          {/* Step 2: Targeting */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <Label>Target Segments</Label>
              <div className="grid gap-2">
                {segments?.map((segment) => (
                  <button
                    key={segment.id}
                    onClick={() => {
                      const selected = form.segment_ids.includes(segment.id)
                        ? form.segment_ids.filter((id) => id !== segment.id)
                        : [...form.segment_ids, segment.id];
                      update("segment_ids", selected);
                    }}
                    className={cn(
                      "flex items-center justify-between rounded-lg border p-3 text-left transition-colors",
                      form.segment_ids.includes(segment.id)
                        ? "border-primary bg-primary/5"
                        : "hover:bg-muted"
                    )}
                  >
                    <div>
                      <p className="font-medium">{segment.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {segment.description}
                      </p>
                    </div>
                    <Badge variant="secondary">
                      {segment.customer_count} customers
                    </Badge>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 3: Content */}
          {currentStep === 2 && (
            <>
              <div className="space-y-2">
                <Label htmlFor="subject">Subject Line</Label>
                <Input
                  id="subject"
                  value={form.content.subject}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      content: { ...prev.content, subject: e.target.value },
                    }))
                  }
                  placeholder="Your subject line here"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="body">Message Body</Label>
                <textarea
                  id="body"
                  className="min-h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={form.content.body}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      content: { ...prev.content, body: e.target.value },
                    }))
                  }
                  placeholder="Write your message..."
                />
              </div>
            </>
          )}

          {/* Step 4: Schedule */}
          {currentStep === 3 && (
            <>
              <div className="space-y-2">
                <Label htmlFor="start">Start Date & Time</Label>
                <Input
                  id="start"
                  type="datetime-local"
                  value={form.schedule.start}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      schedule: { ...prev.schedule, start: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Select
                  value={form.schedule.timezone}
                  onValueChange={(v) =>
                    setForm((prev) => ({
                      ...prev,
                      schedule: { ...prev.schedule, timezone: v },
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="UTC">UTC</SelectItem>
                    <SelectItem value="America/New_York">
                      Eastern (US)
                    </SelectItem>
                    <SelectItem value="America/Chicago">
                      Central (US)
                    </SelectItem>
                    <SelectItem value="America/Denver">
                      Mountain (US)
                    </SelectItem>
                    <SelectItem value="America/Los_Angeles">
                      Pacific (US)
                    </SelectItem>
                    <SelectItem value="Europe/London">London</SelectItem>
                    <SelectItem value="Europe/Paris">Paris</SelectItem>
                    <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          {/* Step 5: A/B Test */}
          {currentStep === 4 && (
            <div className="space-y-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.ab_test.enabled}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      ab_test: {
                        ...prev.ab_test,
                        enabled: e.target.checked,
                      },
                    }))
                  }
                  className="h-4 w-4"
                />
                <span className="text-sm font-medium">
                  Enable A/B Testing
                </span>
              </label>

              {form.ab_test.enabled && (
                <>
                  <div className="space-y-2">
                    <Label>Winning Metric</Label>
                    <Select
                      value={form.ab_test.winning_metric}
                      onValueChange={(v) =>
                        setForm((prev) => ({
                          ...prev,
                          ab_test: { ...prev.ab_test, winning_metric: v },
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="open_rate">Open Rate</SelectItem>
                        <SelectItem value="click_rate">
                          Click Rate
                        </SelectItem>
                        <SelectItem value="conversion_rate">
                          Conversion Rate
                        </SelectItem>
                        <SelectItem value="revenue">Revenue</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-4">
                    <Label>Variants</Label>
                    {["A", "B"].map((variant, i) => (
                      <Card key={variant}>
                        <CardContent className="pt-4 space-y-2">
                          <Label>Variant {variant} Content</Label>
                          <Input
                            placeholder="Subject line"
                            value={
                              form.ab_test.variants[i]?.content?.subject || ""
                            }
                            onChange={(e) => {
                              const variants = [...form.ab_test.variants];
                              variants[i] = {
                                name: `Variant ${variant}`,
                                content: {
                                  ...variants[i]?.content,
                                  subject: e.target.value,
                                  body: variants[i]?.content?.body || "",
                                },
                                traffic_percentage: variant === "A" ? 50 : 50,
                              };
                              setForm((prev) => ({
                                ...prev,
                                ab_test: { ...prev.ab_test, variants },
                              }));
                            }}
                          />
                          <textarea
                            className="min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                            placeholder="Message body"
                            value={
                              form.ab_test.variants[i]?.content?.body || ""
                            }
                            onChange={(e) => {
                              const variants = [...form.ab_test.variants];
                              variants[i] = {
                                name: `Variant ${variant}`,
                                content: {
                                  subject:
                                    variants[i]?.content?.subject || "",
                                  body: e.target.value,
                                },
                                traffic_percentage: variant === "A" ? 50 : 50,
                              };
                              setForm((prev) => ({
                                ...prev,
                                ab_test: { ...prev.ab_test, variants },
                              }));
                            }}
                          />
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Step 6: Review */}
          {currentStep === 5 && (
            <div className="space-y-4">
              <div className="rounded-lg border p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Name</span>
                  <span className="font-medium">{form.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Type</span>
                  <Badge variant="secondary">{form.type}</Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Goal</span>
                  <span>{form.goal}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Segments</span>
                  <span>{form.segment_ids.length} selected</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Schedule</span>
                  <span>{form.schedule.start || "Not set"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">A/B Test</span>
                  <Badge variant={form.ab_test.enabled ? "success" : "secondary"}>
                    {form.ab_test.enabled ? "Enabled" : "Disabled"}
                  </Badge>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
          disabled={currentStep === 0}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        {currentStep < STEPS.length - 1 ? (
          <Button
            onClick={() => setCurrentStep((s) => s + 1)}
            disabled={!canProceed()}
          >
            Next
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleSubmit} disabled={createCampaign.isPending}>
            {createCampaign.isPending ? (
              <>
                <span className="animate-spin mr-2">&#9696;</span>
                Creating...
              </>
            ) : (
              <>
                <Check className="mr-2 h-4 w-4" />
                Launch Campaign
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
