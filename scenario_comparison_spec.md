# Scenario Comparison Page Specification

## Goal
Provide executives with an instant, clear, and data-dense view to compare multiple campaign strategies (Campaign A, Campaign B, Campaign C) side-by-side, making business decisions and identifying the winning strategy obvious at a glance.

## 1. Layout
The layout is designed for maximum data density and executive clarity, prioritizing the "bottom line" up front.

- **Header Section**: Page title, date range selector, and export options (PDF/CSV).
- **Recommendation Banner**: A prominent, full-width alert at the top explicitly stating the AI-recommended scenario and the primary reason (e.g., "Campaign B is recommended for maximizing ROI while maintaining low Churn.").
- **Scenario Ranking Ribbon**: A horizontal summary showing 1st, 2nd, and 3rd place scenarios based on a composite score.
- **Comparison Matrix**: The core data table, locking the metric names on the left and scrolling horizontally if more than 3 scenarios are compared.
- **Visual Comparison Charts**: A section below the matrix using Recharts to visualize the trade-offs (e.g., Radar chart for multi-metric balance, Bar charts for direct Revenue/ROI comparison).

## 2. Component Tree
```text
ScenarioComparisonPage
├── PageHeader (Title, Actions)
├── RecommendationBanner (AI-driven insight)
├── ScenarioRankingRibbon (1st, 2nd, 3rd place cards)
├── ComparisonControls (Add/Remove scenarios to compare)
├── ComparisonMatrix
│   ├── MatrixHeader (Scenario Names, Badges)
│   ├── MetricCategory (e.g., Financials, Engagement)
│   │   ├── MetricRow (Revenue, ROI, etc.)
│   │   │   ├── MetricLabel (with tooltip definition)
│   │   │   ├── ScenarioValueCard (A)
│   │   │   ├── ScenarioValueCard (B)
│   │   │   └── ScenarioValueCard (C)
└── VisualComparisonCharts
    ├── RadarChartComparison (Overall balance)
    └── BarChartComparison (Revenue & LTV side-by-side)
```

## 3. Comparison Matrix
The matrix is structured with metrics as rows and campaigns as columns. 

**Metrics Included:**
- **Financials**: Revenue, ROI, LTV (Lifetime Value)
- **Engagement**: Conversions, Retention
- **Risk & Brand**: Churn, Sentiment

**Design Rules:**
- **Absolute Values & Deltas**: Display the absolute projected value and the delta percentage compared to a baseline (or compared to Campaign A as the control).
- **Color Coding**: Positive deltas in green (`text-green-600`), negative in red (`text-red-600`).
- **ShadCN Implementation**: Use ShadCN `Table` for structure, utilizing sticky headers and first columns.

## 4. Recommendation Engine Display
The recommendation engine output is displayed prominently to guide the executive.

- **Location**: Top of the page, directly under the header.
- **Visuals**: Use a ShadCN `Alert` component with a distinct border or background (e.g., soft blue or brand primary color) to separate it from raw data.
- **Content**: 
  - **Verdict**: "Campaign B is the optimal choice."
  - **Why**: "It yields 15% higher ROI than Campaign A and reduces Churn by 2% compared to Campaign C."
  - **Trade-off**: "Note: Campaign C produces slightly higher Conversions, but at a 20% higher acquisition cost."

## 5. Winner Highlighting
To make the decision obvious, the winning scenario is visually distinct throughout the page.

- **Matrix Column**: The entire column for the winning campaign has a subtle highlight background (e.g., `bg-primary/5` or `bg-green-50/50`).
- **Badges**: A "Winner" or "Recommended" ShadCN `Badge` next to the campaign name in the matrix header.
- **Typography**: The metric values for the winning campaign are bolded (`font-bold`).
- **Chart Emphasis**: In Recharts, the winning campaign's line/bar is fully opaque and uses the primary brand color, while others are slightly muted or use secondary colors.

## 6. Scenario Ranking
A composite ranking system to quickly stack-rank the campaigns.

- **Composite Score**: A normalized score (0-100) calculated backend-side based on weighted metrics.
- **Display**: Three cards at the top (Gold, Silver, Bronze thematic styling, or simply 1st, 2nd, 3rd).
- **Format**:
  - **1st**: Campaign B (Score: 92/100)
  - **2nd**: Campaign C (Score: 85/100)
  - **3rd**: Campaign A (Score: 78/100)

## 7. API Mapping
The frontend expects a unified endpoint to fetch the comparison data to avoid race conditions.

**Endpoint:** `GET /api/v1/scenarios/compare?ids=camp_A,camp_B,camp_C`

**Response Structure (Frontend Contract):**
```typescript
interface ComparisonResponse {
  recommendation: {
    recommendedScenarioId: string;
    summary: string;
    keyTradeoffs: string[];
  };
  rankings: Array<{
    scenarioId: string;
    rank: number;
    compositeScore: number;
  }>;
  scenarios: Array<{
    id: string;
    name: string;
    metrics: {
      revenue: { value: number; deltaPercent: number; isWinner: boolean };
      roi: { value: number; deltaPercent: number; isWinner: boolean };
      conversions: { value: number; deltaPercent: number; isWinner: boolean };
      retention: { value: number; deltaPercent: number; isWinner: boolean };
      churn: { value: number; deltaPercent: number; isWinner: boolean }; // lower is better
      sentiment: { value: number; deltaPercent: number; isWinner: boolean };
      ltv: { value: number; deltaPercent: number; isWinner: boolean };
    }
  }>;
}
```

## 8. Loading States
Executives expect immediate feedback, so the loading experience must feel premium.

- **Initial Load**: Use ShadCN `Skeleton` components mirroring the exact layout of the Comparison Matrix and Charts. 
- **Matrix Skeletons**: A header skeleton row, followed by 7 metric rows. Each cell pulses to indicate data fetching.
- **Chart Skeletons**: A large rectangular skeleton box where the Recharts canvas will render.
- **Recommendation Skeleton**: A text skeleton pulsing in the banner area.
- **Transitions**: When data arrives, use a fast fade-in transition (`animate-in fade-in duration-300`) to prevent jarring layout shifts.
