# TWINCX Executive Dashboard Spec

## 1. Screen Objective

The Executive Dashboard is the first authenticated screen judges see. It must answer four executive questions within 15 seconds:

- **Business Health**: Are revenue, customers, and growth trending in the right direction?
- **Customer Health**: Are digital twins current, engaged, loyal, and low-risk?
- **Campaign Performance**: Are campaigns producing ROI and conversion lift?
- **Future Risk**: What churn, revenue, and simulation risks need action now?

Primary route: `/dashboard`

Primary stack: React, TypeScript, Tailwind, shadcn/ui, Recharts, TanStack Query.

## 2. Full Layout

### Header

Purpose: establish context, freshness, controls, and executive-grade confidence.

Desktop layout:

- Left: `TWINCX Executive Dashboard` title and organization name.
- Center: segmented date range control: `7D`, `30D`, `90D`, `YTD`.
- Right: data freshness label, refresh button, export button, user menu.

Implementation:

- Use shadcn `Button`, `Tabs`, `DropdownMenu`, `Badge`.
- Default range: `30D`.
- Refresh button invalidates dashboard, revenue, churn, campaign, twin, segment, and simulation query keys.
- Show `Last updated 10:42` from client fetch completion time, not backend clock.

### Hero Section

Purpose: provide the 15-second executive readout.

Layout:

- Full-width, 2-column desktop grid.
- Left 60%: headline health summary with one-sentence interpretation.
- Right 40%: four compact score tiles for `Business Health`, `Customer Health`, `Campaign Performance`, and `Future Risk`.

Hero content:

- Main metric: `Executive Health Score`, computed client-side as a weighted score:
  - business: 35%
  - customer: 30%
  - campaign: 20%
  - risk: 15%
- Supporting sentence examples:
  - `Revenue is up, customer risk is controlled, and simulations show positive ROI.`
  - `Revenue is stable, but churn risk and low campaign ROI need action.`
- Use deterministic thresholds so the copy is explainable.

Score tile behavior:

- `Business Health`: revenue trend, total revenue, customer growth proxy.
- `Customer Health`: average engagement, average loyalty, churn rate.
- `Campaign Performance`: average campaign ROI and active campaigns.
- `Future Risk`: churn alerts, simulation probability of loss, stale twin ratio.

Visuals:

- Use shadcn `Card` only for the hero score tiles and repeated widgets.
- Use a compact radial score meter for the Executive Health Score.
- Color states:
  - green: healthy
  - amber: watch
  - red: action required
  - neutral slate only for disabled or unavailable data

### KPI Grid

Purpose: make the business state scannable without opening charts.

Desktop:

- 6 cards in a 6-column grid.
- Each card has an icon, label, value, trend, and sparkline where useful.

Tablet:

- 3 columns.

Mobile:

- 2 columns for compact cards, then 1 column below 380px.

KPI cards:

- Revenue
- Customer Count
- Twin Count
- Average Churn
- Campaign ROI
- Average LTV

### Charts

Purpose: explain movement and composition after the KPI scan.

Desktop chart grid:

- Left 8 columns: `RevenueTrendChart`
- Right 4 columns: `RiskAndHealthPanel`
- Next row left 5 columns: `SegmentBreakdown`
- Next row center 4 columns: `CampaignPerformanceChart`
- Next row right 3 columns: `TwinHealthGauge`

Charts:

- `RevenueTrendChart`: Recharts `ComposedChart` with revenue bars and optional average order value line.
- `RiskAndHealthPanel`: stacked status panel with churn alerts, at-risk count, retention/churn indicators.
- `SegmentBreakdown`: Recharts `PieChart` plus ranked list of top segments.
- `CampaignPerformanceChart`: Recharts `BarChart` for ROI and conversion rate by campaign.
- `TwinHealthGauge`: Recharts `RadialBarChart` or custom progress rings for engagement, loyalty, confidence, staleness.

### Insights

Purpose: convert dashboard data into action.

Bottom section:

- `RecentSimulations`: last 5 simulations with status, expected ROI, expected revenue, risk level.
- `RecommendedActions`: 3 to 5 ranked actions based on churn, campaign ROI, segment opportunity, and simulation results.

Recommended action format:

- severity badge
- action title
- why it matters
- expected impact
- primary CTA

Example:

`Protect high-value at-risk customers`
`5 churn alerts are concentrated in Loyal Buyers. Launch a win-back simulation before the next campaign.`
CTA: `Open Simulation Lab`

## 3. Component Tree

```text
DashboardPage
 ├── DashboardHeader
 │   ├── DateRangeTabs
 │   ├── FreshnessIndicator
 │   ├── RefreshDashboardButton
 │   └── DashboardActionsMenu
 ├── ExecutiveHero
 │   ├── ExecutiveHealthScore
 │   ├── ExecutiveSummaryText
 │   └── HealthScoreGrid
 │       ├── BusinessHealthTile
 │       ├── CustomerHealthTile
 │       ├── CampaignPerformanceTile
 │       └── FutureRiskTile
 ├── KPIGrid
 │   ├── RevenueKPI
 │   ├── CustomerCountKPI
 │   ├── TwinCountKPI
 │   ├── AverageChurnKPI
 │   ├── CampaignROIKPI
 │   └── AverageLTVKPI
 ├── DashboardCharts
 │   ├── RevenueTrendChart
 │   ├── RiskAndHealthPanel
 │   ├── SegmentBreakdown
 │   ├── CampaignPerformanceChart
 │   └── TwinHealthGauge
 ├── InsightsGrid
 │   ├── RecentSimulations
 │   └── RecommendationsPanel
 └── DashboardStateBoundary
     ├── DashboardSkeleton
     ├── DashboardErrorState
     └── DashboardEmptyState
```

Recommended file structure when the frontend is present:

```text
frontend/src/app/(dashboard)/dashboard/page.tsx
frontend/src/components/dashboard/DashboardHeader.tsx
frontend/src/components/dashboard/ExecutiveHero.tsx
frontend/src/components/dashboard/KPIGrid.tsx
frontend/src/components/dashboard/charts/RevenueTrendChart.tsx
frontend/src/components/dashboard/charts/SegmentBreakdown.tsx
frontend/src/components/dashboard/charts/CampaignPerformanceChart.tsx
frontend/src/components/dashboard/RecentSimulations.tsx
frontend/src/components/dashboard/RecommendationsPanel.tsx
frontend/src/hooks/use-dashboard-data.ts
frontend/src/lib/dashboard-mappers.ts
```

## 4. Data Contract

Use one primary aggregate query and focused secondary queries.

Primary query:

`GET /api/v1/analytics/dashboard`

Expected fields:

```ts
type DashboardResponse = {
  stats: {
    total_customers: number;
    events_24h: number;
    active_campaigns: number;
    avg_engagement: number;
    total_revenue: number;
    revenue_growth: number;
    churn_rate: number;
  };
  engagement_trend?: Array<Record<string, unknown>>;
  revenue_data?: Array<Record<string, unknown>>;
  segment_distribution?: Array<Record<string, unknown>>;
  top_segments?: Array<Record<string, unknown>>;
  recent_activity?: Array<Record<string, unknown>>;
  churn_alerts?: Array<Record<string, unknown>>;
};
```

Secondary queries:

- `GET /api/v1/analytics/revenue?granularity=day&start_date={YYYY-MM-DD}&end_date={YYYY-MM-DD}`
- `GET /api/v1/analytics/churn?granularity=day&start_date={YYYY-MM-DD}&end_date={YYYY-MM-DD}`
- `GET /api/v1/analytics/campaigns?start_date={YYYY-MM-DD}&end_date={YYYY-MM-DD}`
- `GET /api/v1/twins/summary`
- `GET /api/v1/customers?page=1&page_size=100&sort_by=created_at&sort_order=desc`
- `GET /api/v1/segments?page=1&page_size=5&sort_by=customer_count&sort_order=desc`
- `GET /api/v1/simulations?page=1&page_size=5&sort_by=created_at&sort_order=desc`
- `GET /api/v1/simulations/{simulation_id}/results` for completed recent simulations only.

Defensive mapping requirements:

- Twin scores from `/api/v1/twins/{customer_id}` and twin summary can be `0.0 - 1.0`; multiply by 100 only for percent display.
- `/api/v1/twins/{customer_id}` may return `last_rebuilt` instead of `built_at`; map both to `lastBuiltAt`.
- `sentiment_trend` can be `number[]` or `{date, score}[]`; normalize before charting.
- Segment refresh route is `/api/v1/segments/{segment_id}/refresh`, not `/compute`.
- Personalized recommendations route is not used on this dashboard because the documented route is unstable.

## 5. Widgets

### Revenue

Purpose: show business traction and whether revenue is accelerating.

Visualization:

- KPI card: total revenue for selected date range.
- Sparkline: last 7 data points from revenue trend.
- Main chart: `RevenueTrendChart` using bars for `revenue` and line for `avg_order_value` when present.

API:

- Primary: `GET /api/v1/analytics/dashboard` -> `stats.total_revenue`, `revenue_data`.
- Detail: `GET /api/v1/analytics/revenue`.

Refresh strategy:

- Refetch every 60 seconds while tab is focused.
- Manual refresh invalidates immediately.
- Cache stale time: 30 seconds.

### Customer Count

Purpose: show market/customer base size.

Visualization:

- KPI card with `total_customers`.
- Optional sublabel: `events_24h` as activity pulse.

API:

- Primary: `GET /api/v1/analytics/dashboard` -> `stats.total_customers`, `stats.events_24h`.
- Fallback: `GET /api/v1/customers?page=1&page_size=1` -> `total`.

Refresh strategy:

- Refetch every 60 seconds.
- Customer count can use cached dashboard payload; do not issue fallback unless primary fails or field is missing.

### Twin Count

Purpose: prove the platform has a live model for the customer base.

Visualization:

- KPI card: `total_twins`.
- Subtext: twin coverage percentage = `total_twins / total_customers`.
- Small health row: average engagement, loyalty, and sentiment.

API:

- Primary: `GET /api/v1/twins/summary`.
- Supporting: `GET /api/v1/analytics/dashboard` for customer denominator.

Refresh strategy:

- Refetch every 60 seconds.
- Refetch on `twin.update` realtime event when available.
- If `/twins/summary` returns 404 because no twins exist, render zero-state instead of erroring the whole dashboard.

### Average Churn

Purpose: communicate customer risk immediately.

Visualization:

- KPI card: churn rate as percentage.
- Risk color:
  - `< 5%` healthy
  - `5% - 12%` watch
  - `> 12%` action required
- `RiskAndHealthPanel` shows churn alerts and at-risk count.

API:

- Primary: `GET /api/v1/analytics/dashboard` -> `stats.churn_rate`, `churn_alerts`.
- Detail: `GET /api/v1/analytics/churn`.

Refresh strategy:

- Refetch every 60 seconds.
- Also refetch after campaign launch, simulation completion, or twin rebuild.

### Campaign ROI

Purpose: show whether marketing spend is efficient.

Visualization:

- KPI card: weighted average ROI from campaigns with results.
- Chart: top campaigns by ROI, with conversion rate as label/tooltip.
- Empty ROI values display as `Pending results`.

API:

- Primary: `GET /api/v1/analytics/campaigns`.
- Optional detail: `GET /api/v1/campaigns/{campaign_id}/results` only when drilling into one campaign.

Refresh strategy:

- Refetch every 60 seconds for active campaigns.
- Refetch every 5 minutes if no active campaigns.
- Refetch immediately after campaign `launch`, `pause`, `cancel`, or `simulate`.

### Average LTV

Purpose: show customer value quality, not just customer volume.

Visualization:

- KPI card: average LTV.
- Formula: average of `ltv` across sampled customers, or `total_ltv / customer_count` for selected segment analytics.
- Trend indicator compares current value to previous loaded range when available.

API:

- Primary fallback path: `GET /api/v1/customers?page=1&page_size=100&sort_by=created_at&sort_order=desc` -> average `data[].ltv`.
- Segment detail: `GET /api/v1/analytics/segments/{segment_id}` -> `total_ltv`, `customer_count`.
- Future backend improvement: add `avg_ltv` to `/api/v1/analytics/dashboard`.

Refresh strategy:

- Refetch every 2 minutes.
- Refetch after twin rebuild or customer event ingestion if realtime events are wired.

### Top Segments

Purpose: identify the largest and most valuable customer groups.

Visualization:

- `SegmentBreakdown` pie/donut using `segment_distribution`.
- Ranked segment list with customer count, engagement, revenue or LTV if available.

API:

- Primary: `GET /api/v1/analytics/dashboard` -> `top_segments`, `segment_distribution`.
- Fallback/enrichment: `GET /api/v1/segments?page=1&page_size=5`.
- Detail on click: `GET /api/v1/analytics/segments/{segment_id}`.

Refresh strategy:

- Refetch every 2 minutes.
- Refetch after segment refresh or customer batch import.

### Recent Simulations

Purpose: show the future-facing value of TWINCX: forecast before spending.

Visualization:

- Table/list of last 5 simulations.
- Columns: name, status, horizon, expected revenue, expected ROI, probability of loss, completed time.
- Status badges: draft, running, completed, failed, cancelled.
- Running simulations show progress bar.

API:

- List: `GET /api/v1/simulations?page=1&page_size=5&sort_by=created_at&sort_order=desc`.
- Status for running rows: `GET /api/v1/simulations/{simulation_id}/status`.
- Results for completed rows: `GET /api/v1/simulations/{simulation_id}/results`.

Refresh strategy:

- Running simulation rows poll status every 3 seconds.
- Completed/failed rows stop polling.
- List refetches every 60 seconds.

### Recommended Actions

Purpose: turn analytics into executive next steps.

Visualization:

- Ranked action cards with severity, action title, driver metric, and CTA.
- Maximum 5 actions.
- Use deterministic rule engine first; do not call unstable recommendations endpoint.

API:

- Derived from:
  - `/api/v1/analytics/dashboard`
  - `/api/v1/analytics/churn`
  - `/api/v1/analytics/campaigns`
  - `/api/v1/twins/summary`
  - `/api/v1/simulations/{id}/results`

Refresh strategy:

- Recompute client-side whenever any source query changes.
- No independent network request.

Rule examples:

- If churn rate > 12% or at-risk customers > 10%: recommend win-back simulation.
- If campaign ROI < 1.0: recommend pausing low-ROI campaigns and testing new segment.
- If twin coverage < 80%: recommend event ingestion or twin rebuild.
- If a simulation has `probability_of_loss > 0.15`: recommend reducing budget or improving targeting.
- If a segment has high engagement and low campaign exposure: recommend campaign expansion.

## 6. Empty States

Dashboard-level empty state:

- Condition: all primary metrics are zero and no charts have data.
- Title: `No executive data yet`
- Body: `Ingest customer events or seed demo data to populate revenue, twins, campaigns, and simulations.`
- CTAs:
  - `Import Customers`
  - `Open Simulation Lab`
  - `View Setup Guide`

Widget empty states:

- Revenue: `No purchase events in this range`
- Customer Count: `No customers found`
- Twin Count: `No twins built yet`
- Average Churn: `Churn unavailable until twins have activity history`
- Campaign ROI: `No completed campaign results`
- Average LTV: `No purchase history available`
- Top Segments: `No segments computed`
- Recent Simulations: `No simulations run yet`
- Recommended Actions: `No action needed from current data`

Empty state rules:

- Empty is not an error.
- Empty widgets keep the same card height as loaded widgets.
- Use shadcn `Button` for only one primary CTA per empty widget.

## 7. Loading States

Initial page load:

- Header renders immediately.
- Hero uses skeleton blocks for score, summary, and four health tiles.
- KPI grid uses six same-size skeleton cards.
- Charts use fixed-height skeleton containers so layout does not shift.

Partial loading:

- If secondary queries load after primary dashboard query, render primary values first and show inline chart skeletons only where needed.
- Refresh button shows spinner and is disabled while any primary refetch is active.
- Running simulations show row-level progress instead of replacing the entire list with a skeleton.

Skeleton dimensions:

- Hero: `min-h-[220px]`
- KPI card: `h-[132px]`
- Revenue chart: `h-[360px]`
- Segment/campaign charts: `h-[300px]`
- Insight panels: `min-h-[360px]`

## 8. Error States

Dashboard-level error:

- Show only when `/api/v1/analytics/dashboard` fails and there is no cached data.
- Message: `Dashboard metrics are unavailable`
- Include request retry button.
- Include support detail in collapsible area: status code, request id when present.

Widget-level error:

- Secondary query failures should not blank the whole dashboard.
- Failed widgets display a compact alert with retry.
- Continue showing any stale cached data with `Showing cached data` badge.

Expected API errors:

- `401`: redirect to `/login` after clearing auth state.
- `403`: render access-denied message inside dashboard shell.
- `404` on `/api/v1/twins/summary`: treat as empty twin state.
- `404` on simulation results: show `Results pending`.
- `500`: show retry and keep cached data when available.

Recommended implementation:

```ts
const dashboardQuery = useQuery({
  queryKey: ['dashboard', dateRange],
  queryFn: getDashboard,
  staleTime: 30_000,
  refetchInterval: 60_000,
  retry: 1,
});
```

## 9. Mobile Strategy

Mobile goal: preserve the 15-second readout without forcing chart inspection.

Breakpoints:

- `<640px`: single-column layout.
- `640px - 1023px`: two-column KPI grid and stacked charts.
- `>=1024px`: full executive grid.

Mobile order:

1. Header compact row: title, date range menu, refresh icon.
2. Executive Hero score and summary.
3. Four health tiles in 2x2 grid.
4. KPI Grid in 2 columns.
5. Revenue chart.
6. Risk panel.
7. Campaign performance.
8. Top segments.
9. Recent simulations.
10. Recommended actions.

Mobile chart rules:

- Charts must have horizontal padding and no clipped axis labels.
- Use simplified axes with max 4 ticks.
- Tooltips must fit within viewport.
- Segment pie becomes a ranked list below 420px.
- Campaign chart becomes horizontal bars below 640px.

Mobile interaction:

- Date range uses shadcn `DropdownMenu`, not horizontal tabs.
- Header action labels collapse to icons with tooltips.
- Tables become list rows; do not require horizontal scrolling for executive metrics.

## 10. Visual System

Dashboard tone: dense, polished, operational, executive. Avoid a marketing landing-page layout.

Recommended Tailwind tokens:

- Page: `bg-background text-foreground`
- Content width: `max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8`
- Section gap: `space-y-6`
- Cards: `rounded-lg border bg-card shadow-sm`
- KPI value: `text-2xl font-semibold tracking-normal`
- Chart title: `text-sm font-medium`
- Supporting text: `text-sm text-muted-foreground`

Icon suggestions:

- Revenue: `DollarSign`
- Customers: `Users`
- Twins: `Network`
- Churn: `AlertTriangle`
- ROI: `TrendingUp`
- LTV: `Gem`
- Simulations: `LineChart`
- Actions: `ListChecks`

Use lucide-react icons inside buttons and KPI cards.

## 11. Derived Metrics

Executive Health Score:

```ts
businessScore = scoreRevenueGrowth(revenueGrowth) * 0.45
  + scoreRevenuePresence(totalRevenue) * 0.35
  + scoreActiveCustomers(totalCustomers) * 0.20;

customerScore = scorePercent(avgEngagement) * 0.35
  + scorePercent(avgLoyalty) * 0.25
  + inverseScore(churnRate) * 0.25
  + scoreTwinCoverage(twinCount, customerCount) * 0.15;

campaignScore = scoreROI(avgCampaignRoi) * 0.60
  + scoreActiveCampaigns(activeCampaigns) * 0.20
  + scoreConversionRate(avgConversionRate) * 0.20;

riskScore = inverseScore(churnRate) * 0.45
  + inverseScore(probabilityOfLoss) * 0.35
  + inverseScore(staleTwinRatio) * 0.20;

executiveHealthScore = businessScore * 0.35
  + customerScore * 0.30
  + campaignScore * 0.20
  + riskScore * 0.15;
```

Display rules:

- `>= 80`: healthy
- `60 - 79`: watch
- `< 60`: action required

Average Campaign ROI:

```ts
avgCampaignRoi = mean(campaigns.filter(c => c.roi != null).map(c => c.roi));
```

Average LTV:

```ts
avgLtv = mean(customers.filter(c => c.ltv > 0).map(c => c.ltv));
```

Twin Coverage:

```ts
twinCoverage = totalCustomers > 0 ? totalTwins / totalCustomers : 0;
```

## 12. Acceptance Criteria

- The first viewport shows header, executive hero, and all six KPI cards on desktop.
- A CEO can identify business health, customer health, campaign performance, and future risk without scrolling.
- All required widgets are present: Revenue, Customer Count, Twin Count, Average Churn, Campaign ROI, Average LTV, Top Segments, Recent Simulations, Recommended Actions.
- Dashboard can render with only `/api/v1/analytics/dashboard` available.
- Secondary API failures are isolated to their widgets.
- Empty, loading, and error states are explicit for every widget.
- Charts use Recharts and are responsive.
- All percent displays normalize `0.0 - 1.0` backend scores to `0 - 100%`.
- No widget depends on the unstable recommendations route.
- Mobile layout has no horizontal page scroll.
