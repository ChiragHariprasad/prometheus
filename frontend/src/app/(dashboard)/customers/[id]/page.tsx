"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useCustomer, useCustomerEvents, useTwin, useTwinPredictions } from "@/hooks/use-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TwinVisualization } from "@/components/twins/twin-visualization";
import { InterestCloud } from "@/components/twins/interest-cloud";
import { format } from "date-fns";
import {
  ArrowLeft,
  Mail,
  Phone,
  MapPin,
  Calendar,
  Tag,
  Activity,
  DollarSign,
  RefreshCw,
  AlertTriangle,
  Target,
  TrendingUp,
  Heart,
} from "lucide-react";
import Link from "next/link";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

export default function CustomerDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [activeTab, setActiveTab] = useState("profile");

  const { data: customer, isLoading: customerLoading } = useCustomer(id);
  const { data: twin, isLoading: twinLoading } = useTwin(id);
  const { data: events } = useCustomerEvents(id);
  const { data: predictions } = useTwinPredictions(id);

  if (customerLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        Customer not found.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/customers">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">{customer.name}</h1>
            <Badge
              variant={
                customer.churn_risk === "high"
                  ? "destructive"
                  : customer.churn_risk === "medium"
                    ? "warning"
                    : "success"
              }
            >
              {customer.churn_risk} churn risk
            </Badge>
          </div>
          <p className="text-muted-foreground">{customer.email}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Activity className="h-4 w-4" />
              Engagement Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{customer.engagement_score}%</p>
            <Progress
              value={customer.engagement_score}
              className={cn(
                "mt-2 h-2",
                customer.engagement_score >= 70
                  ? "[&>div]:bg-engagement-high"
                  : customer.engagement_score >= 40
                    ? "[&>div]:bg-engagement-medium"
                    : "[&>div]:bg-engagement-low"
              )}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Heart className="h-4 w-4" />
              Loyalty Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{customer.loyalty_score}%</p>
            <Progress value={customer.loyalty_score} className="mt-2 h-2" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <DollarSign className="h-4 w-4" />
              Lifetime Value
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              ${(customer.ltv || 0).toLocaleString()}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Calendar className="h-4 w-4" />
              Last Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {customer.last_activity ? format(new Date(customer.last_activity), "MMM d") : "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full justify-start border-b rounded-none h-auto p-0 bg-transparent">
          {[
            "profile",
            "twin",
            "events",
            "predictions",
            "campaigns",
            "recommendations",
          ].map((tab) => (
            <TabsTrigger
              key={tab}
              value={tab}
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent capitalize px-4 py-2"
            >
              {tab}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="profile" className="mt-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">
                  Contact Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <span>{customer.email}</span>
                </div>
                {customer.phone && (
                  <div className="flex items-center gap-2 text-sm">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <span>{customer.phone}</span>
                  </div>
                )}
                <div className="flex items-center gap-2 text-sm">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span>
                    Customer since{" "}
                    {customer.created_at ? format(new Date(customer.created_at), "MMM d, yyyy") : "—"}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">
                  Tags & Segments
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground mb-2">Tags</p>
                  <div className="flex flex-wrap gap-1">
                    {customer.tags.map((tag) => (
                      <Badge key={tag} variant="secondary">
                        <Tag className="mr-1 h-3 w-3" />
                        {tag}
                      </Badge>
                    ))}
                    {customer.tags.length === 0 && (
                      <span className="text-sm text-muted-foreground">
                        No tags
                      </span>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-2">
                    Segments
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {customer.segments.map((segment) => (
                      <Badge key={segment}>{segment}</Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="twin" className="mt-6">
          {twinLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
            </div>
          ) : twin ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Last rebuilt:{" "}
                  {format(new Date(twin.last_rebuilt), "MMM d, yyyy HH:mm")}
                </p>
                <Button variant="outline" size="sm">
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Rebuild Twin
                </Button>
              </div>

              <TwinVisualization twin={twin} />

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">
                    Interests Cloud
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <InterestCloud interests={twin.interests} />
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              No twin data available. Ingest events to generate a twin.
            </div>
          )}
        </TabsContent>

        <TabsContent value="events" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Event Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {events?.data?.map((event) => (
                  <div
                    key={event.id}
                    className="flex items-start gap-3 border-l-2 border-primary/30 pl-4 py-2"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-[10px]">
                          {event.event_type}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          via {event.channel}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {format(new Date(event.timestamp), "MMM d, yyyy HH:mm")}
                      </p>
                    </div>
                  </div>
                ))}
                {(!events?.data || events.data.length === 0) && (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No events recorded yet.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="predictions" className="mt-6">
          {predictions ? (
            <div className="grid gap-6 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <AlertTriangle className="h-4 w-4" />
                    Churn Prediction
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-destructive">
                    {(predictions.churn.probability * 100).toFixed(0)}%
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    within {predictions.churn.timeframe}
                  </p>
                  <div className="mt-3 space-y-1">
                    {predictions.churn.factors.map((factor) => (
                      <Badge
                        key={factor}
                        variant="outline"
                        className="text-[10px]"
                      >
                        {factor}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <DollarSign className="h-4 w-4" />
                    Predicted LTV
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold">
                    ${predictions.ltv.predicted.toLocaleString()}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Range: ${predictions.ltv.range[0].toLocaleString()} - $
                    {predictions.ltv.range[1].toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {(predictions.ltv.confidence * 100).toFixed(0)}% confidence
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <Target className="h-4 w-4" />
                    Next Best Action
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-bold capitalize">
                    {predictions.next_best_action.action.replace("_", " ")}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Expected impact: +
                    {(
                      predictions.next_best_action.expected_impact * 100
                    ).toFixed(0)}
                    %
                  </p>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              No predictions available yet.
            </div>
          )}
        </TabsContent>

        <TabsContent value="campaigns" className="mt-6">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              Campaign history and responses will appear here.
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recommendations" className="mt-6">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              Personalized recommendations will appear here.
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
