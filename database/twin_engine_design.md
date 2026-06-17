# Digital Twin Engine Design

## 1. Twin Data Model

```python
@dataclass
class CustomerTwin:
    customer_id: UUID
    organization_id: UUID
    
    # Behavior Profile
    behavior_profile: BehaviorProfile
    
    # Interest Graph
    interest_graph: InterestGraph
    
    # Channel Affinity
    channel_affinity: ChannelAffinity
    
    # Engagement State
    engagement_score: float  # 0.0 - 1.0
    loyalty_score: float     # 0.0 - 1.0
    lifetime_value: float    # Monetary value
    
    # Temporal State
    sentiment_trend: list[float]  # Last N sentiment scores
    intent_forecast: IntentForecast
    
    # Risk
    risk_indicators: RiskIndicators
    
    # Communication
    communication_preferences: CommunicationPreferences
    
    # Versioning
    version: int
    confidence_score: float
    staleness_score: float
    recalculation_required: bool


@dataclass
class BehaviorProfile:
    # Navigation patterns
    avg_session_duration: float
    sessions_per_week: float
    page_depth_avg: float
    bounce_rate: float
    
    # Purchase behavior
    purchase_frequency: float
    avg_order_value: float
    product_category_affinity: dict[str, float]
    discount_sensitivity: float
    cart_abandonment_rate: float
    
    # Engagement patterns
    email_open_rate: float
    email_click_rate: float
    push_opt_in: bool
    preferred_time_of_day: str
    preferred_day_of_week: str
    
    # Lifecycle
    days_since_first_seen: int
    days_since_last_purchase: int
    days_since_last_engagement: int
    lifecycle_stage: str  # new, active, dormant, churned, reactivated
    
    # Recency-Frequency-Monetary (RFM) scores
    rfm_recency: int      # 1-5
    rfm_frequency: int     # 1-5
    rfm_monetary: int      # 1-5
    rfm_segment: str       # champions, loyal, etc.


@dataclass
class InterestNode:
    category: str
    subcategory: str | None
    interest_level: float     # 0.0 - 1.0
    affinity_score: float     # 0.0 - 1.0
    interaction_count: int
    last_interaction_at: datetime
    first_detected_at: datetime
    decay_factor: float       # Rate of interest decay
    related_interests: list[str]


@dataclass
class InterestGraph:
    nodes: dict[str, InterestNode]  # category -> InterestNode
    edges: list[tuple[str, str, float]]  # (from, to, weight)
    dominant_category: str | None
    interest_diversity: float        # 0.0 - 1.0
    total_interactions: int
    last_updated: datetime


@dataclass
class ChannelAffinity:
    email: ChannelScore
    sms: ChannelScore
    push: ChannelScore
    in_app: ChannelScore
    
    @dataclass
    class ChannelScore:
        channel: str
        engagement_rate: float     # 0.0 - 1.0
        response_rate: float       # 0.0 - 1.0
        conversion_rate: float     # 0.0 - 1.0
        total_interactions: int
        last_interaction_at: datetime
        preference_strength: float # 0.0 - 1.0
        optimal_time: str          # Best time to engage
        optimal_day: str           # Best day to engage


@dataclass
class IntentForecast:
    # Short-term (7 days)
    purchase_intent_7d: float
    engagement_intent_7d: float
    churn_risk_7d: float
    
    # Medium-term (30 days)
    purchase_intent_30d: float
    engagement_intent_30d: float
    churn_risk_30d: float
    
    # Long-term (90 days)
    predicted_ltv_90d: float
    predicted_engagement_90d: float
    
    # Next best action
    recommended_action: str
    recommended_channel: str
    recommended_content: str
    optimal_timing: datetime


@dataclass
class RiskIndicators:
    churn_probability: float           # 0.0 - 1.0
    churn_risk_level: str              # low, medium, high, critical
    churn_triggers: list[str]          # What indicates churn
    churn_prevention_actions: list[str]
    
    # Fatigue indicators
    engagement_decline_rate: float
    negative_sentiment_count: int
    complaint_count: int
    support_ticket_count: int
    unsubscribe_risk: float
    
    # Anomaly detection
    behavior_anomaly_score: float
    last_anomaly_detected_at: datetime
    anomaly_details: dict
```

## 2. Twin Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     TWIN GENERATION PIPELINE                     │
│                                                                  │
│  Step 1: Event Collection                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Kafka Consumer reads customer_events for a given period   │  │
│  │ Window: last 90 days (or configurable)                    │  │
│  │ Batch: 1000 customers per job                             │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                      │
│  Step 2: Feature Computation                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Compute from raw events:                                  │  │
│  │ • Session metrics (duration, pages, bounce)               │  │
│  │ • Purchase metrics (frequency, AOV, categories)           │  │
│  │ • Engagement metrics (open rate, click rate)              │  │
│  │ • Time-based features (recency, trends)                   │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                      │
│  Step 3: Behavior Profile Construction                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • Aggregate metrics into BehaviorProfile                  │  │
│  │ • Compute RFM scores (quantile-based)                     │  │
│  │ • Classify lifecycle stage using rules                    │  │
│  │ • Calculate behavioral trends (7/30/90 day windows)       │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                      │
│  Step 4: Interest Graph Computation                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • Extract categories from events (page views, purchases,  │  │
│  │   searches, content interactions)                         │  │
│  │ • Compute interest levels (frequency * recency decay)     │  │
│  │ • Build affinity scores (proportion of total interactions)│  │
│  │ • Apply time decay to older interests                     │  │
│  │ • Detect emerging interests (short-term spike detection)  │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                      │
│  Step 5: Channel Affinity Computation                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • For each channel: compute engagement/response/conversion│  │
│  │ • Weight by recency (exponential decay)                   │  │
│  │ • Determine optimal time/day from timestamps              │  │
│  │ • Score preference strength (relative to other channels)  │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                      │
│  Step 6: Score Computation                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • Engagement Score = weighted combination of:             │  │
│  │   - Session frequency (30%)                              │  │
│  │   - Page depth (15%)                                     │  │
│  │   - Email engagement (20%)                               │  │
│  │   - Purchase recency (20%)                               │  │
│  │   - Feature usage (15%)                                  │  │
│  │ • Loyalty Score = weighted combination of:                │  │
│  │   - Repeat purchase rate (35%)                           │  │
│  │   - Longevity (25%)                                      │  │
│  │   - NPS/feedback score (15%)                             │  │
│  │   - Referral activity (15%)                              │  │
│  │   - Support interactions (10%)                           │  │
│  │ • Lifetime Value = predicted 12-month revenue             │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                      │
│  Step 7: Validation & Persistence                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • Validate twin completeness (all fields present)         │  │
│  │ • Compute confidence score (based on data density)        │  │
│  │ • Compute staleness score (last event timestamp)          │  │
│  │ • Persist to PostgreSQL (customer_twins table)            │  │
│  │ • Publish twin.update event to Kafka                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Twin Update Pipeline (Real-time)

```
Event arrives on Kafka
        │
        ▼
  ┌──────────────────┐
  │  Event Router    │  Classifies event type
  └────────┬─────────┘
           │
  ┌────────▼─────────┐
  │  Twin Update      │
  │  Dispatcher       │  Routes to specific updaters
  └────────┬─────────┘
           │
     ┌─────┼─────┬──────┬──────┬──────┐
     ▼     ▼     ▼      ▼      ▼      ▼
   Behv  Int   Chnl   Sent   LTV   Risk
   Updtr Updtr AffUp  Updtr  Updtr  Updtr
     │     │     │      │      │      │
     └─────┴─────┴──────┴──────┴──────┘
                    │
              ┌─────▼─────┐
              │  Score    │
              │  Recalc   │
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │ Twin Store│
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │ Publish   │
              │ twin.update│
              └───────────┘

Update Rules:
- Page View: Update behavior profile (session count, time on site)
- Purchase: Update behavior + LTV + interest graph + loyalty
- Email Open: Update channel affinity (email) + engagement
- Email Click: Update channel affinity + interest graph
- Support Ticket: Update risk indicators + sentiment
- Session End: Update behavior profile + engagement score
- Campaign Response: Update channel affinity + engagement
```

## 4. Scoring Algorithms

```python
class TwinScoring:
    
    @staticmethod
    def compute_engagement_score(customer_data: dict) -> float:
        """
        Engagement Score Algorithm:
        - Session frequency (weekly active sessions)
        - Depth of engagement (avg pages per session)
        - Email engagement (open rate * click rate)
        - Purchase recency (days since last purchase)
        - Feature adoption (unique features used)
        """
        session_freq = normalize(customer_data['sessions_per_week'], 0, 20)
        page_depth = normalize(customer_data['avg_page_depth'], 1, 15)
        email_engagement = (
            customer_data['email_open_rate'] * 0.6 +
            customer_data['email_click_rate'] * 0.4
        )
        purchase_recency = recency_score(customer_data['days_since_last_purchase'])
        feature_adoption = normalize(customer_data['features_used_count'], 0, 20)
        
        score = (
            session_freq * 0.25 +
            page_depth * 0.15 +
            email_engagement * 0.20 +
            purchase_recency * 0.25 +
            feature_adoption * 0.15
        )
        return clamp(score, 0.0, 1.0)
    
    @staticmethod
    def compute_loyalty_score(customer_data: dict) -> float:
        """
        Loyalty Score Algorithm:
        - Repeat purchase rate (purchase count / unique customers avg)
        - Customer longevity (days since first seen)
        - NPS / satisfaction (if available)
        - Referral activity (referral count)
        - Support interaction sentiment
        - Account completeness
        """
        repeat_rate = normalize(customer_data['repeat_purchase_ratio'], 0, 1)
        longevity = normalize(customer_data['days_since_first_seen'], 0, 1095)  # 3 years
        nps = normalize(customer_data.get('nps_score', 0), -100, 100)
        referrals = normalize(customer_data.get('referral_count', 0), 0, 20)
        support_sentiment = normalize(customer_data.get('avg_support_sentiment', 0), -1, 1)
        
        score = (
            repeat_rate * 0.35 +
            longevity * 0.20 +
            nps * 0.15 +
            referrals * 0.15 +
            support_sentiment * 0.15
        )
        return clamp(score, 0.0, 1.0)
    
    @staticmethod
    def compute_ltv(customer_data: dict) -> float:
        """
        LTV Algorithm:
        - Traditional: (Average Order Value * Purchase Frequency * Gross Margin) * Average Lifespan
        - ML-enhanced: Use ML model for probabilistic LTV
        
        Simple deterministic LTV for baseline:
        LTV = AOV * monthly_purchase_freq * 12 * avg_retention_years * gross_margin
        """
        aov = customer_data.get('avg_order_value', 0)
        monthly_freq = customer_data.get('purchase_frequency_monthly', 0)
        retention_years = min(
            customer_data.get('days_since_first_seen', 0) / 365 + 
            predict_remaining_lifetime(customer_data),
            10  # Cap at 10 years
        )
        margin = customer_data.get('gross_margin', 0.40)
        
        ltv = aov * monthly_freq * 12 * retention_years * margin
        return max(ltv, 0.0)
    
    @staticmethod
    def compute_sentiment_trend(events: list[dict]) -> list[float]:
        """
        Sentiment Trend:
        - Collect sentiment scores from:
          - Support ticket sentiment
          - Email response sentiment
          - Survey responses
          - Social media mentions
          - Review content
        - Compute 7-day rolling average
        - Store last 30 data points
        """
        sentiment_scores = []
        for event in sorted(events, key=lambda x: x['event_timestamp'], reverse=True)[:30]:
            score = classify_sentiment(event)
            sentiment_scores.append(score)
        return sentiment_scores  # Latest first
    
    @staticmethod
    def compute_staleness(last_event_at: datetime, twin_config: dict) -> float:
        """
        Staleness Score:
        - 0.0 = twin is current
        - 1.0 = twin needs rebuild
        
        Decay function: 1 - e^(-days_since_last_event / half_life)
        Default half_life: 7 days
        """
        if not last_event_at:
            return 1.0
        
        days_since = (datetime.utcnow() - last_event_at).days
        half_life = twin_config.get('staleness_half_life_days', 7)
        
        staleness = 1 - math.exp(-days_since / half_life)
        return clamp(staleness, 0.0, 1.0)
```

## 5. Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 TWIN STORAGE ARCHITECTURE                     │
├─────────────┬──────────────────┬─────────────┬──────────────┤
│  Hot Tier   │  Warm Tier       │  Cold Tier  │  Vector Tier │
│  (Redis)    │  (PostgreSQL)    │  (S3)       │  (Qdrant)    │
├─────────────┼──────────────────┼─────────────┼──────────────┤
│ Active      │ All twin data    │ Historical  │ Embeddings   │
│ twin cache  │ Full profile     │ snapshots   │ for semantic │
│ Session     │ Behavior profile │ 90d+ events │ search &     │
│ data        │ Interest graph   │ Archived    │ similarity   │
│ Real-time   │ Predictions      │ twins       │ clustering   │
│ scores      │ Segments         │             │              │
│ TTL: 24h    │ Persistent       │ Retention:  │ Retention:   │
│             │ (no TTL)         │ 7 years     │ 90 days      │
├─────────────┼──────────────────┼─────────────┼──────────────┤
│ 10ms access │ 50ms access      │ 500ms       │ 20ms access  │
│ 1GB/10K     │ 100GB+ scaling   │ Unlimited   │ 10GB/100K    │
│ customers   │                  │             │ customers    │
└─────────────┴──────────────────┴─────────────┴──────────────┘
```

## 6. Caching Architecture

```python
class TwinCache:
    """
    Redis cache layers for Twin data:
    
    L1: Local memory cache (per pod)
        - TTL: 60 seconds
        - Size: 10K entries
        - Eviction: LRU
    
    L2: Redis cluster
        - TTL: 24 hours (configurable)
        - Sliding window invalidation
        - Write-through for active twins
        - Pub/Sub for invalidation across pods
    
    Cache Keys:
        twin:{org_id}:{customer_id}        -> Full twin JSON
        twin:{org_id}:{customer_id}:scores  -> Score-only (lightweight)
        twin:{org_id}:segment:{segment_id}  -> Customer ID list
        twin:{org_id}:top:engagement        -> Top 100 by engagement
        twin:{org_id}:top:ltv              -> Top 100 by LTV
        twin:{org_id}:churn:critical        -> Critical churn risk
    """
    
    CACHE_PREFIX = "twin:"
    DEFAULT_TTL = 86400  # 24 hours
    
    @staticmethod
    def cache_key(org_id: UUID, customer_id: UUID, suffix: str = "") -> str:
        base = f"{TwinCache.CACHE_PREFIX}{org_id}:{customer_id}"
        return f"{base}:{suffix}" if suffix else base
    
    @staticmethod
    async def get_twin(redis, org_id: UUID, customer_id: UUID) -> dict | None:
        key = TwinCache.cache_key(org_id, customer_id)
        data = await redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    @staticmethod
    async def set_twin(redis, org_id: UUID, customer_id: UUID, twin: dict):
        key = TwinCache.cache_key(org_id, customer_id)
        await redis.setex(key, TwinCache.DEFAULT_TTL, json.dumps(twin))
    
    @staticmethod
    async def invalidate_twin(redis, org_id: UUID, customer_id: UUID):
        """Invalidate twin cache and publish invalidation event"""
        key = TwinCache.cache_key(org_id, customer_id)
        await redis.delete(key)
        await redis.publish("cache:invalidate:twin", json.dumps({
            "organization_id": str(org_id),
            "customer_id": str(customer_id)
        }))
```
