"use client";

import { CampaignBuilder } from "@/components/campaigns/campaign-builder";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function NewCampaignPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/campaigns">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Create Campaign</h1>
          <p className="text-muted-foreground mt-1">
            Build and launch a new marketing campaign
          </p>
        </div>
      </div>

      <CampaignBuilder />
    </div>
  );
}
