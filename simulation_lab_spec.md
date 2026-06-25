# TWINCX Simulation Lab Spec

## 1. Product Objective

Simulation Lab is the centerpiece of the TWINCX demo. It must prove that TWINCX can test campaign strategy before budget is spent by turning customer twins into simulated customer agents, running Monte Carlo outcomes, and producing an executive decision: scale, revise, test smaller, or stop.

Primary route: `/simulation-lab`

Primary stack: React, TypeScript, Tailwind, shadcn/ui, Recharts.

Core workflow:

```text
Configure Campaign
↓
Generate Simulation
↓
Run Simulation
↓
Analyze Outcomes
```

Core message: **Do not spend campaign budget until the twin population has predicted the risk, upside, and next best action.**

## 2. Full Layout

Desktop layout: split workspace with persistent configuration and outcome intelligence.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Header: Simulation Lab | saved simulations | compare | export | run status │
├────────────────────────────┬────────────────────────────────────────────────┤
│ Left Configuration Panel   │ Main Analysis Workspace                        │
│ Campaign + Audience + Cost │ Workflow Stepper                               │
│ Scenario + Model Controls  │ Results KPIs                                   │
│ Generate / Run             │ Scenario / Segment / Timeline / Recommendations│
└────────────────────────────┴────────────────────────────────────────────────┘
```

Recommended desktop grid:

- Left panel: `380px`, sticky, independent scroll.
- Main panel: `minmax(760px, 1fr)`, independent scroll.
- Page max width: `1440px`.
- First viewport must show configuration readiness, workflow status, expected revenue, expected ROI, expected churn, and expected LTV impact.

Header:

- Title: `Simulation Lab`
- Subtitle: `Forecast campaign outcomes before launch`
- Controls:
  - saved simulations dropdown
  - compare runs button
  - export report button
  - refresh button
  - current run status badge

Main workspace sections:

1. `SimulationWorkflowStepper`
2. `ExecutiveOutcomeStrip`
3. `ScenarioResultsPanel`
4. `SegmentAnalysisPanel`
5. `SimulationTimeline`
6. `RecommendationPanel`

Mobile:

- Header compresses actions into icon menu.
- Configuration panel becomes the first accordion section.
- Results appear before advanced charts after a simulation completes.
- Segment and recommendation panels stack vertically.

## 3. Component Tree

```text
SimulationLabPage
 ├── SimulationLabHeader
 │   ├── SavedSimulationSelect
 │   ├── CompareRunsButton
 │   ├── ExportSimulationReportButton
 │   └── SimulationStatusBadge
 ├── SimulationLabShell
 │   ├── SimulationConfigurationPanel
 │   │   ├── CampaignBasicsForm
 │   │   ├── AudienceSegmentSelector
 │   │   ├── OfferAndChannelControls
 │   │   ├── BudgetAndEconomicsControls
 │   │   ├── ModelSettingsControls
 │   │   ├── ScenarioPresetSelector
 │   │   └── SimulationActionBar
 │   └── SimulationAnalysisWorkspace
 │       ├── SimulationWorkflowStepper
 │       ├── ExecutiveOutcomeStrip
 │       │   ├── ExpectedRevenueCard
 │       │   ├── ExpectedROICard
 │       │   ├── ExpectedChurnCard
 │       │   └── ExpectedLTVImpactCard
 │       ├── ScenarioResultsPanel
 │       │   ├── BestCaseCard
 │       │   ├── ExpectedCaseCard
 │       │   ├── WorstCaseCard
 │       │   ├── RevenueDistributionChart
 │       │   ├── ConfidenceIntervalChart
 │       │   └── RiskAssessmentPanel
 │       ├── SegmentAnalysisPanel
 │       │   ├── SegmentResponseChart
 │       │   ├── SegmentRevenueShareChart
 │       │   └── SegmentOutcomeTable
 │       ├── SimulationTimeline
 │       │   ├── RunProgressTimeline
 │       │   ├── ForecastMilestones
 │       │   └── RunHistoryTable
 │       └── RecommendationPanel
 │           ├── NextBestActionCard
 │           ├── RecommendationList
 │           ├── SensitivityDrivers
 │           └── ApplyRecommendationActions
 └── SimulationStateBoundary
     ├── SimulationDraftState
     ├── SimulationRunningState
     ├── SimulationResultSkeleton
     ├── SimulationErrorState
     └── SimulationEmptyState
```

Suggested files:

```text
frontend/src/app/(dashboard)/simulation-lab/page.tsx
frontend/src/components/simulation/SimulationConfigurationPanel.tsx
frontend/src/components/simulation/SimulationWorkflowStepper.tsx
frontend/src/components/simulation/ExecutiveOutcomeStrip.tsx
frontend/src/components/simulation/ScenarioResultsPanel.tsx
frontend/src/components/simulation/SegmentAnalysisPanel.tsx
frontend/src/components/simulation/SimulationTimeline.tsx
frontend/src/components/simulation/RecommendationPanel.tsx
frontend/src/hooks/use-simulation-lab.ts
frontend/src/lib/simulation-mappers.ts
```

## 4. Simulation Configuration Panel

Purpose: let a judge build a campaign scenario quickly and understand what assumptions drive the forecast.

Panel sections:

### Campaign Basics

Fields:

- Simulation name
- Description
- Campaign source:
  - `Create from scratch`
  - `Use existing campaign`
- Campaign type: lifecycle, promotion, win-back, retention, upsell.
- Goal: revenue, retention, engagement, reactivation.

API:

- Existing campaigns: `GET /api/v1/campaigns?page=1&page_size=50`
- Optional campaign details: `GET /api/v1/campaigns/{campaign_id}`

### Audience Segment Selector

Fields:

- Segment multi-select.
- Sample size.
- Include control group toggle.
- Audience estimate.

API:

- `GET /api/v1/segments?page=1&page_size=100`
- Optional segment context: `GET /api/v1/analytics/segments/{segment_id}`

UI:

- Segment cards show name, customer count, dynamic/static badge, last refreshed date.
- If no segments exist, allow synthetic all-customer simulation and show a notice.

### Offer and Channel Controls

Fields:

- Channel: email, SMS, push, in-app, WhatsApp.
- Offer type: discount, bundle, free shipping, new arrival, clearance, loyalty, referral.
- Discount rate: slider `0% - 50%`.
- Urgency: low, medium, high.
- Frequency: stepper `1 - 7 touches`.
- Creative type: text, image, video, personalized.
- Competitor pressure: slider `0% - 100%`.

Mapped fields:

- `agent_configuration.channel`
- `agent_configuration.offer_type`
- `agent_configuration.discount_rate`
- `agent_configuration.urgency`
- `agent_configuration.frequency`
- `agent_configuration.creative_type`
- `agent_configuration.competitor_pressure`

### Budget and Economics Controls

Fields:

- Average order value.
- Cost per contact.
- Fixed campaign cost.
- Budget cap.
- Expected reach.

Mapped fields:

- `parameters.avg_order_value`
- `parameters.cost_per_contact`
- `parameters.fixed_cost`
- `parameters.customer_count`

### Model Settings Controls

Fields:

- Monte Carlo iterations: default `1000`.
- Time horizon: default `30 days`.
- Confidence level: default `95%`.
- Scenario preset: best case, expected case, worst case.

Mapped fields:

- `monte_carlo_iterations`
- `time_horizon_days`
- `confidence_level`
- `sample_size`
- `agent_configuration.scenario`

### Action Bar

Buttons:

- `Generate Simulation`
- `Run Simulation`
- `Reset`
- `Save Draft`

Backend behavior note:

- Current `POST /api/v1/simulations` creates the simulation and starts a background run automatically.
- The UI should still show the desired workflow. After `Generate Simulation`, transition immediately into `Run Simulation` status if the backend returns a running simulation.
- The `Run Simulation` button calls `POST /api/v1/simulations/{simulation_id}/run` only for draft or failed simulations.

Create payload:

```ts
const payload = {
  name,
  description,
  type: 'campaign',
  campaign_id: selectedCampaignId ?? null,
  segment_ids: selectedSegmentIds,
  sample_size,
  include_control,
  monte_carlo_iterations,
  confidence_level,
  time_horizon_days,
  parameters: {
    avg_order_value,
    cost_per_contact,
    fixed_cost,
    customer_count: sample_size,
  },
  agent_configuration: {
    channel,
    offer_type,
    discount_rate,
    urgency,
    frequency,
    creative_type,
    scenario,
    competitor_pressure,
  },
  expected_outputs: [
    'revenue',
    'roi',
    'churn',
    'ltv_impact',
    'segment_response',
    'confidence_intervals',
  ],
};
```

## 5. Scenario Results Panel

Purpose: make the forecast decision obvious: what happens if we launch this campaign?

Top KPI strip:

- Expected Revenue
- Expected ROI
- Expected Churn
- Expected LTV Impact

Field mapping:

- Expected Revenue: `expected_outcomes.expected_revenue` or `campaign_impact.expected_revenue`.
- Expected ROI: `expected_outcomes.expected_roi` or `campaign_impact.expected_roi`.
- Expected Churn: `expected_outcomes.expected_churns`, `aggregated_metrics.churn_rate`, or `risk_assessment.churn_risk_level`.
- Expected LTV Impact: `expected_outcomes.ltv_impact` or `customer_projections.ltv_impact`.

Scenario cards:

- Best Case: `monte_carlo_distribution.scenarios.best_case`.
- Expected Case: `monte_carlo_distribution.scenarios.expected_case`.
- Worst Case: `monte_carlo_distribution.scenarios.worst_case`.

Each scenario card shows:

- revenue
- conversions
- open rate
- click rate
- conversion rate
- interpretation label

Charts:

- `RevenueDistributionChart`: Recharts `BarChart` using `monte_carlo_distribution.histogram`.
- `ConfidenceIntervalChart`: Recharts `ComposedChart` with expected revenue line and interval bands.
- `ScenarioComparisonChart`: Recharts `BarChart` comparing best/expected/worst revenue and conversions.
- `RiskAssessmentPanel`: probability of loss, value at risk, expected shortfall, upside potential, sentiment risk.

Confidence intervals:

- Prefer current engine keys:
  - `confidence_intervals.revenue_95`
  - `confidence_intervals.revenue_90`
  - `confidence_intervals.roi`
  - `confidence_intervals.conversions`
  - `confidence_intervals.open_rate`
  - `confidence_intervals.click_rate`
- Support legacy key `confidence_intervals.revenue`.

Decision badge:

- `Scale`: ROI > 2.0 and probability of loss < 10%.
- `Proceed`: ROI > 1.0 and probability of loss < 20%.
- `Test Small`: ROI > 0 and probability of loss < 35%.
- `Revise`: ROI <= 0 or probability of loss >= 35%.
- `Stop`: worst case is negative ROI and churn risk is high.

## 6. Segment Analysis Panel

Purpose: show that TWINCX does not just predict an average. It identifies which customer groups respond, convert, churn, and create value.

Data source:

- `segment_projections`.

Current modeled segment keys:

- `vip`
- `loyal`
- `new`
- `at_risk`
- `inactive`

Segment metrics:

- count
- response rate
- conversion rate
- revenue
- average revenue per customer
- share of revenue

Visualizations:

- `SegmentResponseChart`: horizontal bar chart for response rate and conversion rate.
- `SegmentRevenueShareChart`: stacked bar or pie chart for revenue share.
- `SegmentOutcomeTable`: sortable table with count, response, conversion, revenue, ARPC, recommended action.

Recommended segment actions:

- VIP: scale if high revenue share and low churn.
- Loyal: upsell if conversion is strong.
- New: nurture if response is high but conversion is low.
- At-risk: reduce frequency if churn is elevated.
- Inactive: suppress or use win-back if response is low.

Selected segment context:

- If user selected real customer segments, show a small `Targeted Segments` strip above modeled response cohorts.
- The current engine may map simulations to synthetic cohorts even when real segment IDs are provided. The UI should label modeled cohorts as `Simulated response cohorts` to avoid implying unsupported precision.

## 7. Recommendation Panel

Purpose: turn simulation output into a clear boardroom decision.

Inputs:

- `recommendations`
- `campaign_impact.next_best_action`
- `aggregated_metrics.sensitivity`
- `risk_assessment`
- `expected_outcomes`

Layout:

- Top: `Next Best Action` card.
- Middle: ranked recommendations list.
- Bottom: sensitivity drivers and apply-to-config controls.

Next Best Action card:

- Recommended channel.
- Recommended discount.
- Recommended frequency.
- Rationale.
- Expected impact.

Field mapping:

- `campaign_impact.next_best_action.recommended_channel`
- `campaign_impact.next_best_action.recommended_discount`
- `campaign_impact.next_best_action.recommended_frequency`
- `campaign_impact.next_best_action.actions[]`

Recommendation list:

- Use `recommendations[]` strings from results.
- Convert each to severity:
  - critical: negative ROI, pause, high churn, high loss probability.
  - warning: low open/click/purchase rate, competitor pressure.
  - opportunity: strong ROI, scale audience, increase frequency.
  - neutral: balanced risk-reward.

Sensitivity drivers:

- Use `aggregated_metrics.sensitivity[]`.
- Display impact bars with positive/negative direction.
- Fields: parameter, impact, direction.

Apply controls:

- `Apply recommended channel` updates configuration channel.
- `Apply recommended discount` updates discount rate.
- `Apply recommended frequency` updates frequency.
- `Run revised simulation` creates a new simulation from updated config.

## 8. Simulation Timeline

Purpose: make the workflow visible and reassure judges that the simulation is executing a defensible process.

Workflow timeline:

1. Configure campaign assumptions.
2. Generate simulation record.
3. Build simulated customer agents.
4. Run Monte Carlo iterations.
5. Aggregate outcomes.
6. Compute confidence intervals.
7. Generate recommendations.
8. Ready for campaign decision.

Run progress timeline:

- Shows status: draft, running, completed, failed, cancelled.
- Progress bar from `GET /api/v1/simulations/{simulation_id}/progress`.
- Status details from `GET /api/v1/simulations/{simulation_id}/status`.
- Run details from `GET /api/v1/simulations/{simulation_id}/runs`.

Forecast milestones:

- Day 0: campaign spend starts.
- Day 7: early response read.
- Day 14: conversion signal.
- Day 30: revenue, churn, LTV impact.
- Use `time_horizon_days` to scale milestones.

Chart:

- Recharts `LineChart` or `AreaChart`.
- If `GET /forecast` only returns aggregate values, generate a visual timeline client-side:
  - cumulative revenue ramps from 0 to expected revenue.
  - confidence band widens over time.
  - churn/LTV impact appears as secondary markers.
- Label as `Forecast shape derived from aggregate simulation output`.

Run history table:

- run number
- seed
- status
- agents count
- iterations executed
- runtime seconds
- started/completed timestamps
- error message if failed

## 9. API Mapping

### Campaign and Segment Setup

List campaigns:

- `GET /api/v1/campaigns?page=1&page_size=50`

Get campaign:

- `GET /api/v1/campaigns/{campaign_id}`

List segments:

- `GET /api/v1/segments?page=1&page_size=100`

Segment analytics:

- `GET /api/v1/analytics/segments/{segment_id}`

Churn context:

- `GET /api/v1/analytics/churn`

### Simulation Lifecycle

List simulations:

- `GET /api/v1/simulations?page=1&page_size=20&sort_by=created_at&sort_order=desc`

Create and generate simulation:

- `POST /api/v1/simulations`
- Returns `SimulationResponse`.
- Current backend auto-runs after creation.

Get simulation:

- `GET /api/v1/simulations/{simulation_id}`
- Completed simulations may include nested `results` and `forecast`.

Run simulation:

- `POST /api/v1/simulations/{simulation_id}/run`
- Use only when status is draft or failed.

Status:

- `GET /api/v1/simulations/{simulation_id}/status`

Progress:

- `GET /api/v1/simulations/{simulation_id}/progress`

Results:

- `GET /api/v1/simulations/{simulation_id}/results`

Forecast:

- `GET /api/v1/simulations/{simulation_id}/forecast`

Runs:

- `GET /api/v1/simulations/{simulation_id}/runs`

### Normalized Result Type

```ts
type NormalizedSimulationResult = {
  expectedRevenue: number;
  expectedRoi: number;
  expectedChurns: number;
  churnRate: number;
  ltvImpact: number;
  expectedConversions: number;
  expectedOpenRate: number;
  expectedClickRate: number;
  expectedConversionRate: number;
  expectedCost: number;
  expectedProfit: number;
  probabilityOfLoss: number;
  valueAtRisk95: number;
  expectedShortfall: number;
  upsidePotential: number;
  sentimentShift: number;
  sentimentRisk: string;
  churnRiskLevel: string;
  revenue95: [number, number];
  revenue90: [number, number];
  roiInterval: [number, number];
  conversionInterval: [number, number];
  scenarios: {
    best_case?: Scenario;
    expected_case?: Scenario;
    worst_case?: Scenario;
  };
  segmentProjections: Record<string, SegmentProjection>;
  recommendations: string[];
  sensitivity: Array<{ parameter: string; impact: number; direction: string }>;
  nextBestAction?: {
    recommended_channel: string;
    recommended_discount: number;
    recommended_frequency: number;
    actions: Array<{ action: string; rationale: string; expected_impact: string }>;
  };
};
```

### Mapping Helpers

```ts
function getRevenueInterval(ci: Record<string, unknown>): [number, number] {
  return (ci.revenue_95 as [number, number])
    ?? (ci.revenue as [number, number])
    ?? [0, 0];
}

function formatRoi(roi?: number | null) {
  if (roi == null) return '0.0x';
  return `${roi.toFixed(2)}x`;
}

function formatPercent(value?: number | null) {
  if (value == null) return '0%';
  return `${Math.round(value * 100)}%`;
}
```

### Polling Strategy

- After create: poll status/progress every 2 seconds while status is running.
- Poll results every 3 seconds while running; stop when results are available or status is failed.
- Fetch forecast and runs after completion.
- Invalidate simulations list after create, run, failure, or completion.

## 10. Loading States

Initial page:

- Configuration panel renders immediately.
- Main workspace shows `SimulationDraftState` with the workflow, explanation, and disabled result placeholders.

Generating simulation:

- Disable form fields that affect payload.
- Show inline spinner on `Generate Simulation`.
- Add stepper state: `Generating simulation record`.

Running simulation:

- Replace result placeholders with live running state.
- Show:
  - progress bar
  - iterations label
  - simulated agents count if available
  - elapsed time
  - current step in timeline
- Keep configuration visible but locked.

Loading completed results:

- Show KPI skeleton cards:
  - `h-[120px]`
- Scenario panel skeleton:
  - `h-[360px]`
- Segment panel skeleton:
  - `h-[320px]`
- Recommendations skeleton:
  - `min-h-[280px]`

Partial loading:

- If results are loaded but forecast is not, show results and mark timeline as `Forecast loading`.
- If runs fail to load, only the run history table shows an error.
- If segment analytics fail, the simulation result segment projections still render.

## 11. Error States

Configuration errors:

- Missing simulation name.
- No segment selected and sample size is zero.
- Invalid confidence level.
- Iterations less than 1.
- Time horizon less than 1 day.
- Negative cost or average order value.

Use inline shadcn form messages and keep the generate button disabled until valid.

Create simulation error:

- Show alert in action bar: `Could not generate simulation`.
- Include retry.
- Keep form values intact.

Run simulation error:

- Show `Simulation failed` panel with:
  - failure reason if returned by run history
  - retry run button
  - duplicate and edit configuration button

Results unavailable:

- If `GET /results` returns 404 while status is running: show `Results pending`.
- If `GET /results` returns 404 after completed: show `Results were not saved` and retry.

Forecast unavailable:

- Show derived timeline from results.
- Do not block analysis.

Expected API errors:

- `401`: clear auth and redirect to `/login`.
- `403`: show access denied in page shell.
- `404` simulation: show not found with saved simulation selector.
- `409` run conflict: refetch status and show current run state.
- `422`: map validation messages into configuration form.
- `500`: keep cached result if present and show retry.

## 12. Empty States

No simulations:

- Main workspace shows `Build your first campaign simulation`.
- CTA: `Configure campaign`.

No campaigns:

- Campaign source selector still supports `Create from scratch`.
- Existing campaign dropdown shows `No campaigns available`.

No segments:

- Segment selector shows `No saved segments`.
- Allow synthetic cohort simulation with sample size.

No recommendations:

- Show `No recommendations generated`.
- Provide deterministic fallback:
  - positive ROI + low risk: proceed.
  - negative ROI: reduce budget or targeting.
  - high churn risk: reduce frequency.
  - high loss probability: run smaller A/B test.

## 13. Visual System

Tone: investor-grade decision lab, not a generic form page.

Layout:

- Quiet, dense, analytical.
- Configuration is persistent.
- Results use executive KPI cards and high-signal charts.
- Avoid marketing hero sections.

Components:

- shadcn `Card`, `Tabs`, `Button`, `Select`, `Slider`, `Input`, `Switch`, `Badge`, `Table`, `Alert`, `Progress`, `Tooltip`, `ScrollArea`.
- Recharts `BarChart`, `ComposedChart`, `AreaChart`, `LineChart`, `PieChart`.

Icon suggestions:

- Configure: `SlidersHorizontal`
- Generate: `Sparkles`
- Run: `Play`
- Analyze: `BarChart3`
- Revenue: `DollarSign`
- ROI: `TrendingUp`
- Churn: `AlertTriangle`
- LTV: `Gem`
- Confidence: `ShieldCheck`
- Recommendation: `ListChecks`

Color rules:

- Revenue/profit positive: green.
- Risk/churn/loss: amber to red.
- Confidence intervals: muted blue bands.
- Best case: green.
- Expected case: blue.
- Worst case: red/amber.

## 14. Acceptance Criteria

- The page clearly shows the workflow: Configure Campaign -> Generate Simulation -> Run Simulation -> Analyze Outcomes.
- A judge can see expected revenue, expected ROI, expected churn, expected LTV impact, segment response, confidence intervals, best case, expected case, worst case, and recommendations.
- The configuration form maps directly to `SimulationCreate`.
- Running simulations poll status/progress and transition automatically into results.
- Scenario results use `SimulationResultResponse` without invented required backend fields.
- Segment analysis renders from `segment_projections`.
- Recommendations render from both `recommendations[]` and `campaign_impact.next_best_action`.
- Loading and error states are scoped so one failed enrichment does not break the page.
- The page supports current backend behavior where creating a simulation automatically starts a run.
- The page visually communicates that campaign budget should be tested against customer twins before launch.
