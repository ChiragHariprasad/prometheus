# TWINCX Twin Explorer Spec

## 1. Product Objective

The Twin Explorer is the flagship page of TWINCX. It must make a judge understand, without explanation, that a Customer Digital Twin is a live behavioral model of a customer: what they do, what they care about, what they remember, how they feel, what they are likely to do next, and what action the business should take.

Primary route: `/twins`

Primary user: CEO, CMO, Investor, Growth Lead.

Primary stack: React, TypeScript, Tailwind, shadcn/ui, Recharts.

Core message: **TWINCX turns customer event history into a predictive, actionable customer model.**

## 2. Page Layout

Desktop layout: three-panel command center.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Header: Twin Explorer | customer search | segment filter | refresh/rebuild  │
├───────────────┬───────────────────────────────────────┬─────────────────────┤
│ Left Panel    │ Center Panel                          │ Right Panel         │
│ Customer      │ Digital Twin Visualization            │ Predictions         │
│ Summary       │ Behavior + Interest + Memory          │ Recommendations     │
│ Timeline      │ Sentiment + Evolution                 │ Next Best Action    │
└───────────────┴───────────────────────────────────────┴─────────────────────┘
```

Recommended desktop grid:

- Left panel: `300px`
- Center panel: `minmax(620px, 1fr)`
- Right panel: `360px`
- Page height: `calc(100vh - dashboard shell header)`
- Panels scroll independently.

Header:

- Left: `Twin Explorer` title and live twin status badge.
- Center: searchable customer combobox with avatar, name, email, and churn badge.
- Right: `Rebuild Twin`, `Export Snapshot`, `Open Customer`, and refresh icon.

First viewport:

- Left: selected customer profile and key health scores.
- Center: large interactive twin visualization with behavior rings, interest graph, memory stream, sentiment line.
- Right: LTV, churn, purchase intent, and next best action.

Bottom center tabs:

- `Behavior`
- `Memory`
- `Sentiment`
- `Engagement`
- `Campaigns`
- `Raw Signals`

## 3. Component Tree

```text
TwinExplorerPage
 ├── TwinExplorerHeader
 │   ├── CustomerSearchCombobox
 │   ├── SegmentFilterDropdown
 │   ├── TwinFreshnessBadge
 │   ├── RebuildTwinButton
 │   └── TwinActionsMenu
 ├── TwinExplorerShell
 │   ├── LeftPanel
 │   │   ├── CustomerSummaryCard
 │   │   ├── TwinScoreStack
 │   │   ├── ChannelAffinityMiniChart
 │   │   ├── CustomerTimeline
 │   │   └── CustomerSegments
 │   ├── CenterPanel
 │   │   ├── DigitalTwinCanvas
 │   │   │   ├── TwinCoreNode
 │   │   │   ├── BehaviorOrbit
 │   │   │   ├── InterestGraphLayer
 │   │   │   ├── MemoryPulseLayer
 │   │   │   └── RiskSignalLayer
 │   │   ├── TwinInsightTabs
 │   │   │   ├── BehaviorProfilePanel
 │   │   │   ├── InterestGraphPanel
 │   │   │   ├── MemoryTimelinePanel
 │   │   │   ├── SentimentAnalysisPanel
 │   │   │   ├── BehavioralEvolutionPanel
 │   │   │   ├── EngagementHistoryPanel
 │   │   │   └── CampaignHistoryPanel
 │   │   └── TwinSignalInspector
 │   └── RightPanel
 │       ├── PredictionCards
 │       │   ├── LTVPredictionCard
 │       │   ├── ChurnPredictionCard
 │       │   ├── PurchaseIntentCard
 │       │   └── EngagementIntentCard
 │       ├── NextBestActionCard
 │       ├── RecommendationList
 │       ├── RiskDrivers
 │       └── ActionImpactPreview
 └── TwinExplorerStateBoundary
     ├── TwinExplorerSkeleton
     ├── TwinExplorerEmptyState
     └── TwinExplorerErrorState
```

Suggested file structure:

```text
frontend/src/app/(dashboard)/twins/page.tsx
frontend/src/components/twins/TwinExplorerHeader.tsx
frontend/src/components/twins/CustomerSummaryCard.tsx
frontend/src/components/twins/DigitalTwinCanvas.tsx
frontend/src/components/twins/InterestGraphPanel.tsx
frontend/src/components/twins/MemoryTimelinePanel.tsx
frontend/src/components/twins/BehavioralEvolutionPanel.tsx
frontend/src/components/twins/PredictionCards.tsx
frontend/src/components/twins/RecommendationList.tsx
frontend/src/components/twins/CustomerTimeline.tsx
frontend/src/hooks/use-twin-explorer.ts
frontend/src/lib/twin-mappers.ts
```

## 4. Left Panel: Customer Summary

Purpose: anchor the digital twin to a real customer and show why this person matters.

Sections:

- Customer identity: avatar initials, name, email, external ID.
- Lifecycle: lifecycle stage, RFM segment, first seen, last activity.
- Value: lifetime value, average order value, purchase frequency.
- Health scores: engagement, loyalty, confidence, staleness.
- Channel affinity: email, SMS, push, in-app.
- Segments: badges for segment memberships.
- Customer timeline: recent behavior events.

Customer Summary Card:

- Display name: `first_name last_name`, fallback to email.
- Primary chips: lifecycle stage, churn risk, active/inactive.
- Secondary facts: location, locale, timezone, source.

Twin Score Stack:

- Four vertical meters:
  - Engagement
  - Loyalty
  - Confidence
  - Staleness
- Convert `0.0 - 1.0` scores to percentages for display.
- Staleness is inverted visually: low staleness is healthy, high staleness is warning.

Customer Timeline:

- Compact chronological feed using event icons.
- Group by day.
- Show event type, channel, campaign badge, value, and timestamp.
- Event examples:
  - purchase
  - page_view
  - email_open
  - email_click
  - support_ticket
  - campaign_response

## 5. Center Panel: Digital Twin Visualization

Purpose: create the visual moment that explains what a digital twin is.

Design:

- Large interactive SVG or React-rendered canvas-style surface.
- Central node is the customer twin.
- Surrounding orbit layers represent behavior, interests, memory, sentiment, and risk.
- Selecting any node updates `TwinSignalInspector`.

Central Twin Node:

- Shows customer initials or avatar.
- Ring 1: engagement score.
- Ring 2: loyalty score.
- Ring 3: confidence score.
- Outer pulse: staleness score.
- Status badge: built, active, stale, rebuilding.

Behavior Orbit:

- Nodes: sessions, purchases, email engagement, recency, page depth, support, channel response.
- Node size = score strength.
- Node color = healthy/watch/risk.
- On hover: show raw metric and contribution to behavior profile.

Interest Graph Layer:

- Category nodes positioned around the twin.
- Edge thickness = related affinity or co-occurrence.
- Node size = affinity score or interaction count.
- Dominant category is visually emphasized.

Memory Pulse Layer:

- Animated short arcs moving from recent events into the twin core.
- Arc type maps to event source:
  - purchase: revenue signal
  - support: risk/sentiment signal
  - campaign: response signal
  - page/session: behavior signal
- Animation should be subtle and pause on reduced-motion preference.

Risk Signal Layer:

- Churn, fatigue, complaints, negative sentiment, and behavior anomaly indicators.
- Risk nodes sit outside the core graph and connect to affected behavior or memory nodes.

Implementation:

- Use React + SVG for the central visualization.
- Use Recharts for supporting trend charts below the visualization.
- Use shadcn `Tooltip`, `Tabs`, `ScrollArea`, `Badge`, `Card`.

## 6. Right Panel: Predictions and Recommendations

Purpose: show that the twin is predictive and actionable.

Prediction cards:

- LTV
- Churn
- Purchase Intent
- Engagement Intent
- Next Best Action

LTV Card:

- Primary value: `lifetime_value` or latest LTV prediction.
- Secondary: predicted 90-day LTV when available.
- Visualization: mini area trend or confidence sparkline.

Churn Card:

- Primary value: churn probability.
- Label: low, medium, high, critical.
- Drivers: churn triggers, staleness, engagement decline, complaints.
- CTA: `Run win-back simulation` or `Create retention campaign`.

Purchase Intent Card:

- Primary value: 7-day and 30-day purchase intent.
- Visualization: two stacked progress bars.
- CTA: `Send next best offer`.

Next Best Action Card:

- Title from `intent_forecast.recommended_action`, `twin_output.next_best_action`, or top recommendation.
- Include channel, timing, and reason.
- Show expected impact if available:
  - churn reduction
  - revenue opportunity
  - engagement lift

Recommendation List:

- Ranked actions from personalized recommendations and deterministic twin rules.
- Show score, category, source, and applied state.
- Feedback controls: thumbs up/down or `Applied` state can call recommendation feedback endpoint.

## 7. Interest Graph Design

Purpose: show what the customer cares about and how those interests relate.

Primary visualization:

- Force-style radial graph implemented with SVG.
- Center: customer twin node.
- First ring: dominant categories.
- Second ring: subcategories or related interests.
- Edges connect related interests.

Node encoding:

- Size: `affinity_score` or `weight`.
- Color: interest category family.
- Border intensity: recency.
- Opacity: decay factor or confidence.

Panel detail:

- Top categories ranked list.
- Interest diversity score.
- Total interactions.
- Emerging interests badge for categories with recent spikes.

Data normalization:

```ts
type InterestNode = {
  id: string;
  label: string;
  affinity: number;
  interactionCount: number;
  lastInteractionAt?: string;
  relatedInterests: string[];
};
```

Fallback rules:

- Prefer `twin.interest_graph.nodes`.
- If unavailable, use `twin.interests`.
- If unavailable, use `GET /api/v1/customers/{customer_id}/interests`.
- If still unavailable, derive categories from recent events where `event_properties.category` exists.

## 8. Memory Timeline Design

Purpose: show that the twin remembers behavior, purchases, campaigns, and channel preferences.

Memory Timeline layout:

- Vertical timeline with event groups.
- Left rail: date and source icon.
- Main body: memory card.
- Right edge: signal impact indicators.

Memory types:

- Purchase memory: category, value, frequency, LTV impact.
- Campaign memory: delivered/opened/clicked/converted, campaign name, channel.
- Channel memory: preferred channel, response rate, optimal time/day.
- Support memory: sentiment impact, complaint count, risk trigger.
- Behavioral memory: session depth, page views, cart abandonment.

Memory Profile panels:

- `Campaign Responses`: campaign response sequence and conversion outcomes.
- `Purchase Categories`: ranked purchase categories and values.
- `Channel History`: email/SMS/push/in-app affinity.
- `Seasonality Patterns`: best day/time, recurring behavior.
- `Discount Sensitivity`: value meter with explanation in tooltip.

Timeline interactions:

- Click a memory item to highlight linked nodes in Digital Twin Visualization.
- Filter chips: all, purchases, campaigns, support, engagement.
- Search inside memory timeline for event type or campaign.

## 9. Behavioral Evolution Design

Purpose: prove the twin changes over time, not a static CRM profile.

Visuals:

- Recharts `ComposedChart` for engagement, loyalty, sentiment, and purchases over time.
- Recharts `RadarChart` for current behavior profile sub-scores.
- Recharts `BarChart` for channel affinity.
- Snapshot slider for twin history.

Behavior Profile Panel:

- Score radar:
  - engagement
  - purchase activity
  - session depth
  - communication response
  - recency
- Metric rows:
  - sessions per week
  - average session duration
  - page depth average
  - bounce rate
  - purchase frequency
  - average order value
  - cart abandonment rate
  - email open/click rate

Behavioral Evolution Panel:

- Timeline chart with:
  - engagement score
  - loyalty score
  - sentiment score
  - purchase events
  - campaign touches
- Snapshot comparison:
  - `Before`
  - `Current`
  - `Predicted`

Engagement History:

- Derived from events.
- Chart:
  - events per day
  - active sessions
  - channel distribution
  - email opens/clicks
- Use event icons on the chart for major events: purchases, complaints, campaign conversions.

Campaign History:

- Derived from customer events with `campaign_id`.
- Show campaign cards with channel, status, response, revenue, and engagement score.
- If campaign target details are available, show treatment, priority, delivered/opened/clicked/converted times.

## 10. Sentiment Analysis

Purpose: show emotional state and risk direction.

Visuals:

- Recharts `AreaChart` for sentiment trend.
- Current sentiment badge: negative, neutral, positive.
- Trigger list: support tickets, complaints, negative feedback, recent inactivity.

Data mapping:

- Prefer `twin.sentiment_trend`.
- Accept either `number[]` or `{date: string; score: number}[]`.
- If missing, derive sentiment proxy from events:
  - purchase: positive
  - email click/campaign response: mildly positive
  - support ticket/complaint: negative
  - inactivity/staleness: risk signal, not sentiment score

Display rules:

- Normalize sentiment to `-1.0` to `1.0`.
- Use zero baseline line.
- Highlight last 7 days.

## 11. API Mapping

### Required Queries

Customer list/search:

- `GET /api/v1/customers?page=1&page_size=20&search={query}`
- Purpose: select customer.

Customer summary:

- `GET /api/v1/customers/{customer_id}`
- Fields: name, email, lifecycle-adjacent metadata, engagement score, loyalty score, churn risk, LTV, last activity.

Digital twin:

- `GET /api/v1/twins/{customer_id}`
- Current returned fields include:
  - `customer_id`
  - `status`
  - `engagement_score`
  - `loyalty_score`
  - `confidence_score`
  - `staleness_score`
  - `sentiment_score`
  - `churn_probability`
  - `interests`
  - `interest_graph`
  - `channel_affinity`
  - `sentiment_trend`
  - `last_rebuilt`
- Preferred rich fields when backend returns full schema:
  - `behavior_profile`
  - `memory_profile`
  - `intent_forecast`
  - `risk_indicators`
  - `twin_output`
  - `lifetime_value`
  - `version`
  - `built_at`

Twin rebuild:

- `POST /api/v1/twins/{customer_id}/rebuild`
- Use for `Rebuild Twin` button.

Twin history:

- `GET /api/v1/twins/{customer_id}/history?limit=50`
- Purpose: behavioral evolution snapshots.

Predictions:

- `GET /api/v1/twins/{customer_id}/predictions?limit=20`
- Optional:
  - `GET /api/v1/twins/{customer_id}/predictions/churn`
  - `GET /api/v1/twins/{customer_id}/predictions/ltv`
  - `GET /api/v1/twins/{customer_id}/predictions/intent`

Customer timeline:

- `GET /api/v1/customers/{customer_id}/events?page=1&page_size=100`
- Fields: event type, channel, source, value, currency, campaign ID, event properties, timestamp.

Customer interests fallback:

- `GET /api/v1/customers/{customer_id}/interests`

Customer segments:

- `GET /api/v1/customers/{customer_id}/segments`

Recommendations:

- `GET /api/v1/recommendations/{customer_id}/personalized?limit=10`
- Do not call `GET /api/v1/recommendations/{customer_id}`; it is documented as mismatched.

Recommendation feedback:

- `POST /api/v1/recommendations/feedback`

Campaign history enrichment:

- `GET /api/v1/campaigns?page=1&page_size=100`
- Match events by `campaign_id`.
- For a selected campaign:
  - `GET /api/v1/campaigns/{campaign_id}/results`
  - `GET /api/v1/campaigns/{campaign_id}/targets?page=1&page_size=100`

### Data Normalization

```ts
type NormalizedTwin = {
  customerId: string;
  status: string;
  engagementScore: number;
  loyaltyScore: number;
  confidenceScore: number;
  stalenessScore: number;
  lifetimeValue?: number;
  churnProbability?: number;
  purchaseIntent7d?: number;
  purchaseIntent30d?: number;
  nextBestAction?: string;
  recommendedChannel?: string;
  behaviorProfile?: BehaviorProfile;
  interestNodes: InterestNode[];
  memoryItems: MemoryItem[];
  sentimentTrend: Array<{ date: string; score: number }>;
  channelAffinity: Record<string, number>;
  lastBuiltAt?: string;
};
```

Score utility:

```ts
function toPercent(score?: number | null) {
  if (score == null) return 0;
  return score <= 1 ? Math.round(score * 100) : Math.round(score);
}
```

Sentiment utility:

```ts
function normalizeSentimentTrend(input: unknown[]) {
  return input.map((item, index) => {
    if (typeof item === 'number') return { date: `day-${index}`, score: item };
    const row = item as { date?: string; score?: number };
    return { date: row.date ?? `day-${index}`, score: row.score ?? 0 };
  });
}
```

Memory utility:

```ts
function buildMemoryItems(twin: NormalizedTwin, events: EventResponse[]) {
  return events.map(event => ({
    id: event.id,
    type: event.event_type,
    channel: event.channel,
    campaignId: event.campaign_id,
    value: event.value,
    timestamp: event.event_timestamp ?? event.ingested_at,
    properties: event.event_properties,
  }));
}
```

## 12. Loading States

Initial loading:

- Render the three-panel layout immediately.
- Left panel skeleton: avatar, customer metadata, four score bars, timeline rows.
- Center panel skeleton: central twin node placeholder, orbit ring placeholders, chart blocks.
- Right panel skeleton: four prediction cards and recommendation rows.

Progressive loading order:

1. Customer list.
2. Selected customer summary.
3. Twin core.
4. Events timeline.
5. Predictions.
6. Recommendations.
7. Campaign enrichment.
8. Twin history snapshots.

Skeleton dimensions:

- Left panel customer card: `h-[220px]`
- Center visualization: `h-[460px]`
- Center tabs: `min-h-[340px]`
- Right prediction card: `h-[116px]`
- Recommendation list: `min-h-[260px]`

Loading behavior:

- If twin is loading but customer is loaded, show customer summary and a center `Building twin model` skeleton.
- If recommendations are loading, keep prediction cards visible.
- If campaign enrichment is loading, render campaign history from events first and fill names/metrics later.
- Rebuild action shows toast/progress and invalidates twin, predictions, history, and customer summary queries.

## 13. Error States

Page-level error:

- Use only when no selected customer can be loaded.
- Message: `Customer data is unavailable`
- Actions: retry, return to customers.

Twin-level error:

- If `GET /api/v1/twins/{customer_id}` fails:
  - Keep customer summary visible.
  - Center panel shows `Twin unavailable`.
  - CTA: `Rebuild Twin`.

Prediction error:

- Show prediction cards with unavailable state.
- Do not block twin visualization.
- CTA: retry predictions.

Timeline error:

- Show compact alert inside Customer Timeline and Memory Timeline.
- Keep behavior/interest/prediction panels usable.

Recommendations error:

- If personalized recommendations fail, use deterministic fallbacks from twin:
  - high churn -> win-back campaign
  - high purchase intent -> targeted offer
  - stale twin -> rebuild twin
  - low confidence -> ingest more events

Expected API errors:

- `401`: clear auth and redirect to `/login`.
- `403`: show access denied in page shell.
- `404` customer: show customer not found with search.
- `404` twin summary/history/results: render empty state for that section.
- `500`: show retry; preserve stale cached data if available.

## 14. Empty States

No selected customer:

- Show search-first state in the center panel.
- CTA: `Select a customer`.

No twin:

- Show customer summary and a large center CTA: `Build Digital Twin`.
- Explain through data placeholders: behavior, interests, memory, predictions will populate after event ingestion.

No interests:

- Interest graph shows a neutral core with `No active interests detected`.
- Suggest ingesting page, purchase, or campaign events.

No memory:

- Memory timeline shows `No remembered interactions`.
- CTA: `View event ingestion`.

No predictions:

- Prediction cards show `Awaiting model output`.
- CTA: `Refresh predictions`.

No campaigns:

- Campaign History shows `No campaign touches for this customer`.

## 15. Visual System

The page should feel like an operational digital twin console, not a CRM profile page.

Layout style:

- Dense but breathable.
- Three independent panels.
- No hero marketing section.
- Use real data as the visual asset: graph, timeline, charts.

Colors:

- Engagement: blue
- Loyalty: green
- Sentiment: teal/amber/red by score
- Interest graph: categorical colors with restrained saturation
- Churn/risk: amber to red
- Memory: neutral with colored source icons

Cards:

- Use `rounded-lg`, border, subtle shadow.
- Do not nest cards inside cards.
- Graph surface can be a single framed tool area.

Typography:

- Compact labels: `text-xs text-muted-foreground`
- Card values: `text-2xl font-semibold`
- Panel titles: `text-sm font-medium`
- Avoid oversized marketing type.

Icons:

- Customer: `User`
- Behavior: `Activity`
- Interest: `Network`
- Memory: `History`
- Sentiment: `SmilePlus`
- LTV: `DollarSign`
- Churn: `AlertTriangle`
- Purchase intent: `ShoppingCart`
- Next best action: `Sparkles`
- Campaign: `Megaphone`

## 16. Acceptance Criteria

- The first viewport clearly shows a customer, their digital twin, predictions, and next best action.
- The page includes Behavior Profile, Interest Graph, Memory Profile, Sentiment Analysis, Predictions, LTV, Churn, Purchase Intent, Next Best Action, Customer Timeline, Engagement History, and Campaign History.
- The center visualization makes the twin feel like a live model, not a static contact record.
- All charts use Recharts or native React/SVG where graph interaction is needed.
- All controls use shadcn/ui primitives.
- The page works with current backend quirks:
  - score scaling
  - `last_rebuilt` timestamp
  - sentiment trend object arrays
  - recommendation personalized route
  - missing rich twin fields
- Loading and error states are scoped by panel and do not blank the whole page unless customer loading fails.
- Mobile layout is usable as stacked sections:
  - customer summary
  - twin visualization
  - predictions
  - timelines
  - history tabs
