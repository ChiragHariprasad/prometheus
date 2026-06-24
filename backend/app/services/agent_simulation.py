import uuid
import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.twin import CustomerTwin


SEGMENTS = ("vip", "loyal", "new", "at_risk", "inactive")
SEGMENT_WEIGHTS = (0.05, 0.15, 0.25, 0.30, 0.25)

CHANNELS = ("email", "sms", "push", "in_app", "whatsapp")

SATURATION_DECAY = 0.85
SENTIMENT_DECAY_PER_TOUCH = 0.005
CHURN_THRESHOLD = 0.75
CHURN_SENTIMENT_FLOOR = -0.6

SCENARIO_MULTIPLIERS: dict[str, dict[str, float]] = {
    "best_case": {
        "engagement": 1.15,
        "loyalty": 1.10,
        "channel_affinity": 1.15,
        "budget": 1.20,
        "churn_resist": 0.80,
        "interest_match": 1.15,
        "conversion": 1.15,
        "sentiment_positive": 1.25,
        "seasonality": 1.10,
    },
    "expected_case": {
        "engagement": 1.0,
        "loyalty": 1.0,
        "channel_affinity": 1.0,
        "budget": 1.0,
        "churn_resist": 1.0,
        "interest_match": 1.0,
        "conversion": 1.0,
        "sentiment_positive": 1.0,
        "seasonality": 1.0,
    },
    "worst_case": {
        "engagement": 0.85,
        "loyalty": 0.90,
        "channel_affinity": 0.85,
        "budget": 0.80,
        "churn_resist": 1.30,
        "interest_match": 0.85,
        "conversion": 0.85,
        "sentiment_positive": 0.75,
        "seasonality": 0.90,
    },
}


@dataclass
class CustomerAgent:
    agent_id: str
    engagement: float
    loyalty: float
    sentiment: float
    interests: list[str]
    disposable_budget: float
    monthly_spending_limit: float
    channel_affinity: dict[str, float]
    churn_risk: float
    purchase_probability: float
    lifetime_value: float
    segment: str = "regular"
    channel_touch_count: dict[str, int] = field(default_factory=dict)
    monthly_spent: float = 0.0

    def copy(self) -> "CustomerAgent":
        return CustomerAgent(
            agent_id=self.agent_id,
            engagement=self.engagement,
            loyalty=self.loyalty,
            sentiment=self.sentiment,
            interests=list(self.interests),
            disposable_budget=self.disposable_budget,
            monthly_spending_limit=self.monthly_spending_limit,
            channel_affinity=dict(self.channel_affinity),
            churn_risk=self.churn_risk,
            purchase_probability=self.purchase_probability,
            lifetime_value=self.lifetime_value,
            segment=self.segment,
            channel_touch_count=dict(self.channel_touch_count),
            monthly_spent=self.monthly_spent,
        )


@dataclass
class CampaignConfig:
    channel: str
    offer_type: str
    discount_rate: float
    urgency: str
    frequency: int
    creative_type: str
    avg_order_value: float = 100.0
    cost_per_contact: float = 0.5
    fixed_cost: float = 5000.0
    scenario: str = "expected_case"
    competitor_pressure: float = 0.0


class SeasonalityModel:
    def __init__(self, rng: random.Random):
        self.rng = rng

    def compute_multiplier(self) -> float:
        day_of_week = self.rng.randint(0, 6)
        is_weekend = day_of_week >= 5
        weekend_boost = 1.20 if is_weekend else 1.0

        is_holiday = self.rng.random() < 0.03
        holiday_boost = 1.30 if is_holiday else 1.0

        season_month = self.rng.randint(1, 12)
        seasonal_boost = 1.0
        if season_month in (11, 12):
            seasonal_boost = 1.20
        elif season_month in (6, 7, 8):
            seasonal_boost = 1.10
        elif season_month in (1, 2):
            seasonal_boost = 0.90

        return round(weekend_boost * holiday_boost * seasonal_boost, 4)


class SocialInfluenceModel:
    def __init__(self, rng: random.Random):
        self.rng = rng

    def compute_referral_probability(self, agent: CustomerAgent, campaign: CampaignConfig, scenario_mult: dict) -> float:
        base = 0.02 * (1.0 + agent.loyalty)
        if campaign.offer_type == "referral":
            base += 0.10
        boosted = base * scenario_mult.get("conversion", 1.0)
        return min(boosted, 0.5)

    def generate_referrals(self, agents: list[CustomerAgent], purchase_count: int, scenario_mult: dict) -> int:
        referrals = 0
        for _ in range(min(purchase_count, len(agents))):
            ref_prob = 0.05 * scenario_mult.get("conversion", 1.0)
            if self.rng.random() < ref_prob:
                referrals += 1
                peer = self.rng.choice(agents)
                peer.engagement = min(peer.engagement + 0.03 * scenario_mult.get("engagement", 1.0), 1.0)
                peer.loyalty = min(peer.loyalty + 0.02 * scenario_mult.get("loyalty", 1.0), 1.0)
        return referrals


class BehaviorModel:
    @staticmethod
    def _sigmoid(x: float, steepness: float = 10.0, midpoint: float = 0.5) -> float:
        return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))

    @staticmethod
    def open_probability(
        agent: CustomerAgent,
        campaign: CampaignConfig,
        scenario_mult: dict,
        seasonality: float,
    ) -> float:
        channel_score = agent.channel_affinity.get(campaign.channel, 0.1) * scenario_mult.get("channel_affinity", 1.0)
        base = agent.engagement * scenario_mult.get("engagement", 1.0) * channel_score
        open_p = BehaviorModel._sigmoid(base, steepness=8.0, midpoint=0.3)

        touch_count = agent.channel_touch_count.get(campaign.channel, 0)
        saturation = SATURATION_DECAY ** touch_count
        open_p *= saturation

        competition_penalty = 1.0 - campaign.competitor_pressure * 0.3
        open_p *= competition_penalty

        open_p *= seasonality
        return min(max(open_p, 0.01), 0.99)

    @staticmethod
    def interest_match(agent: CustomerAgent, campaign: CampaignConfig, scenario_mult: dict) -> float:
        if not agent.interests:
            return 0.3 * scenario_mult.get("interest_match", 1.0)
        category_map = {
            "discount": "sale",
            "bundle": "package",
            "free_shipping": "shipping",
            "new_arrival": "new",
            "clearance": "clearance",
            "loyalty": "reward",
            "referral": "referral",
        }
        campaign_tag = category_map.get(campaign.offer_type, campaign.offer_type)
        matches = sum(1 for i in agent.interests if campaign_tag in i.lower() or i.lower() in campaign_tag)
        base = matches / max(len(agent.interests), 1)
        im = min(base + 0.2, 1.0) if base > 0 else 0.2
        return min(im * scenario_mult.get("interest_match", 1.0), 1.0)

    @staticmethod
    def budget_factor(agent: CustomerAgent, campaign: CampaignConfig, scenario_mult: dict) -> float:
        effective_price = campaign.avg_order_value * (1.0 - campaign.discount_rate)
        if effective_price <= 0:
            return 1.0
        budget_boost = scenario_mult.get("budget", 1.0)
        effective_budget = agent.disposable_budget * budget_boost
        if effective_budget <= 0:
            return 0.1

        immediate = effective_budget / effective_price
        monthly_remaining = max(agent.monthly_spending_limit - agent.monthly_spent, 0)
        monthly_constraint = monthly_remaining / effective_price if effective_price > 0 else 1.0
        return min(immediate, monthly_constraint, 1.0)

    @staticmethod
    def click_probability(
        agent: CustomerAgent,
        campaign: CampaignConfig,
        opened: bool,
        scenario_mult: dict,
        seasonality: float,
    ) -> float:
        if not opened:
            return 0.0
        return BehaviorModel.open_probability(agent, campaign, scenario_mult, seasonality) \
            * BehaviorModel.interest_match(agent, campaign, scenario_mult)

    @staticmethod
    def purchase_probability(
        agent: CustomerAgent,
        campaign: CampaignConfig,
        clicked: bool,
        scenario_mult: dict,
        seasonality: float,
        click_prob: float = 0.0,
    ) -> float:
        if not clicked:
            return 0.0
        cp = click_prob if click_prob > 0 else (
            BehaviorModel.open_probability(agent, campaign, scenario_mult, seasonality)
            * BehaviorModel.interest_match(agent, campaign, scenario_mult)
        )
        discount_appeal = min(campaign.discount_rate * 2.0, 1.0)
        purchase_drive = (agent.loyalty * scenario_mult.get("loyalty", 1.0) + discount_appeal) / 2.0
        base = cp * purchase_drive * BehaviorModel.budget_factor(agent, campaign, scenario_mult)
        return min(base * scenario_mult.get("conversion", 1.0), 0.99)

    @staticmethod
    def sentiment_shift(
        agent: CustomerAgent,
        campaign: CampaignConfig,
        purchased: bool,
        scenario_mult: dict,
    ) -> float:
        if purchased:
            return round(0.06 * (1.0 + agent.loyalty) * scenario_mult.get("sentiment_positive", 1.0), 4)
        if campaign.frequency > 3:
            return round(-0.04 * scenario_mult.get("churn_resist", 1.0), 4)
        return round(-0.015 * scenario_mult.get("churn_resist", 1.0), 4)

    @staticmethod
    def churn_impact(
        agent: CustomerAgent,
        campaign: CampaignConfig,
        opened: bool,
        scenario_mult: dict,
    ) -> float:
        if not opened:
            fatigue = 0.03 * (campaign.frequency - 1) * scenario_mult.get("churn_resist", 1.0)
            return min(fatigue, 0.15)
        if agent.sentiment < CHURN_SENTIMENT_FLOOR:
            return 0.02 * scenario_mult.get("churn_resist", 1.0)
        return 0.0


class AgentGenerator:
    INTEREST_POOL = [
        "electronics", "fashion", "home", "sports", "books",
        "food", "beauty", "toys", "automotive", "music",
        "sale", "premium", "new", "clearance", "reward",
    ]

    @staticmethod
    def synthetic(count: int, seed: int | None = None) -> list[CustomerAgent]:
        rng = random.Random(seed)
        agents: list[CustomerAgent] = []

        for i in range(count):
            segment = rng.choices(SEGMENTS, weights=SEGMENT_WEIGHTS, k=1)[0]
            base_engagement = rng.betavariate(2, 5)
            base_loyalty = rng.betavariate(2, 5)

            if segment == "vip":
                base_engagement = rng.betavariate(9, 2)
                base_loyalty = rng.betavariate(9, 1)
                disposable_budget = rng.lognormvariate(math.log(2000), 0.6)
                monthly_limit = rng.lognormvariate(math.log(5000), 0.5)
            elif segment == "loyal":
                base_engagement = rng.betavariate(6, 2)
                base_loyalty = rng.betavariate(7, 2)
                disposable_budget = rng.lognormvariate(math.log(1000), 0.6)
                monthly_limit = rng.lognormvariate(math.log(2000), 0.5)
            elif segment == "new":
                base_engagement = rng.betavariate(4, 3)
                base_loyalty = rng.betavariate(3, 4)
                disposable_budget = rng.lognormvariate(math.log(300), 0.7)
                monthly_limit = rng.lognormvariate(math.log(800), 0.6)
            elif segment == "at_risk":
                base_engagement = rng.betavariate(2, 5)
                base_loyalty = rng.betavariate(2, 5)
                disposable_budget = rng.lognormvariate(math.log(200), 0.7)
                monthly_limit = rng.lognormvariate(math.log(500), 0.6)
            else:
                base_engagement = rng.betavariate(1, 7)
                base_loyalty = rng.betavariate(1, 6)
                disposable_budget = rng.lognormvariate(math.log(100), 0.7)
                monthly_limit = rng.lognormvariate(math.log(200), 0.6)

            num_interests = rng.randint(1, 5)
            interests = rng.sample(AgentGenerator.INTEREST_POOL, num_interests)

            channel_affinity: dict[str, float] = {}
            for ch in CHANNELS:
                base = rng.betavariate(3, 5)
                if segment == "vip":
                    base = rng.betavariate(8, 2)
                elif segment == "loyal":
                    base = rng.betavariate(6, 3)
                elif segment == "inactive":
                    base = rng.betavariate(1, 7)
                channel_affinity[ch] = round(base, 4)

            sentiment = max(-1.0, min(1.0, rng.gauss(0.2, 0.4)))
            churn_risk = round(1.0 - (base_engagement * 0.4 + base_loyalty * 0.6), 4)
            purchase_prob = round(base_loyalty * rng.betavariate(3, 3), 4)
            ltv = round(disposable_budget * rng.betavariate(2, 3) * 3, 2)

            agents.append(CustomerAgent(
                agent_id=str(uuid.uuid4()),
                engagement=round(base_engagement, 4),
                loyalty=round(base_loyalty, 4),
                sentiment=round(sentiment, 4),
                interests=interests,
                disposable_budget=round(disposable_budget, 2),
                monthly_spending_limit=round(monthly_limit, 2),
                channel_affinity=channel_affinity,
                churn_risk=churn_risk,
                purchase_probability=purchase_prob,
                lifetime_value=ltv,
                segment=segment,
            ))
        return agents

    @staticmethod
    async def from_db(
        session: AsyncSession, organization_id: uuid.UUID,
        campaign: CampaignConfig, limit: int = 10000,
    ) -> list[CustomerAgent]:
        stmt = (
            select(CustomerTwin)
            .where(CustomerTwin.organization_id == str(organization_id))
            .limit(limit)
        )
        result = await session.execute(stmt)
        twins = list(result.scalars().all())

        if not twins:
            logger.info("No twins found, falling back to synthetic agents")
            return AgentGenerator.synthetic(limit)

        agents: list[CustomerAgent] = []
        for twin in twins:
            meta = twin.twin_metadata or {}
            memory = twin.memory_profile or {}
            interest = twin.interest_graph or {}

            interests = [n.get("category", "general") for n in interest.get("nodes", []) if n.get("category")]

            ch_history = memory.get("channel_history", [])
            channel_affinity = {
                ch.get("channel", "email"): round(min(ch.get("count", 0) / 50.0, 1.0), 4)
                for ch in ch_history
            }
            for ch in CHANNELS:
                channel_affinity.setdefault(ch, 0.1)

            db_segment = meta.get("loyalty_segment", "regular")
            segment_map = {
                "champion": "vip",
                "loyal": "loyal",
                "regular": "new",
                "at_risk": "at_risk",
                "inactive": "inactive",
            }
            segment = segment_map.get(db_segment, "new")

            agents.append(CustomerAgent(
                agent_id=str(twin.customer_id),
                engagement=twin.engagement_score or 0.5,
                loyalty=twin.loyalty_score or 0.5,
                sentiment=meta.get("current_sentiment", 0.0),
                interests=interests,
                disposable_budget=0.0,
                monthly_spending_limit=0.0,
                channel_affinity=channel_affinity,
                churn_risk=(twin.risk_indicators or {}).get("churn_probability", 0.3),
                purchase_probability=0.0,
                lifetime_value=twin.lifetime_value or 0.0,
                segment=segment,
            ))
        return agents


class SimulationEngine:
    def __init__(
        self,
        agents: list[CustomerAgent],
        campaign: CampaignConfig,
        seed: int | None = None,
    ):
        self.base_agents = agents
        self.campaign = campaign
        self.rng = random.Random(seed)
        self.seasonality_model = SeasonalityModel(self.rng)
        self.social_model = SocialInfluenceModel(self.rng)
        self.scenario_mult = SCENARIO_MULTIPLIERS.get(
            campaign.scenario, SCENARIO_MULTIPLIERS["expected_case"]
        )
        self._segment_indices: dict[str, list[int]] = {}
        for i, a in enumerate(agents):
            self._segment_indices.setdefault(a.segment, []).append(i)

    def run(self, iterations: int = 1000) -> dict[str, Any]:
        all_results: list[dict[str, Any]] = []

        for it in range(iterations):
            agents = [a.copy() for a in self.base_agents]
            self.rng.shuffle(agents)

            iteration = self._run_iteration(agents)
            all_results.append(iteration)

            if (it + 1) % 100 == 0:
                logger.info("Simulation progress", extra={
                    "iteration": it + 1, "total": iterations,
                })

        return self._aggregate(all_results)

    def _run_iteration(self, agents: list[CustomerAgent]) -> dict[str, Any]:
        seasonality = self.seasonality_model.compute_multiplier()
        seasonality *= self.scenario_mult.get("seasonality", 1.0)

        total_opens = 0
        total_clicks = 0
        total_purchases = 0
        total_revenue = 0.0
        total_churns = 0
        total_referrals = 0
        sentiment_before = 0.0
        sentiment_after = 0.0
        ltv_before = 0.0
        ltv_after = 0.0

        segment_opens: dict[str, int] = {s: 0 for s in SEGMENTS}
        segment_purchases: dict[str, int] = {s: 0 for s in SEGMENTS}
        segment_revenue: dict[str, float] = {s: 0.0 for s in SEGMENTS}

        for agent in agents:
            sentiment_before += agent.sentiment
            ltv_before += agent.lifetime_value

            touched = False
            for touch in range(self.campaign.frequency):
                agent.channel_touch_count[self.campaign.channel] = \
                    agent.channel_touch_count.get(self.campaign.channel, 0) + 1

                open_prob = BehaviorModel.open_probability(agent, self.campaign, self.scenario_mult, seasonality)
                opened = self.rng.random() < open_prob
                if opened:
                    touched = True
                    total_opens += 1
                    segment_opens[agent.segment] = segment_opens.get(agent.segment, 0) + 1

                    click_prob = BehaviorModel.click_probability(agent, self.campaign, opened, self.scenario_mult, seasonality)
                    clicked = self.rng.random() < click_prob
                    if clicked:
                        total_clicks += 1
                        purchase_prob = BehaviorModel.purchase_probability(
                            agent, self.campaign, clicked, self.scenario_mult, seasonality, click_prob
                        )
                        purchased = self.rng.random() < purchase_prob
                        if purchased:
                            total_purchases += 1
                            segment_purchases[agent.segment] = segment_purchases.get(agent.segment, 0) + 1
                            purchase_value = self.campaign.avg_order_value * (1.0 - self.campaign.discount_rate)
                            total_revenue += purchase_value
                            agent.lifetime_value += purchase_value
                            agent.monthly_spent += purchase_value
                            agent.sentiment += BehaviorModel.sentiment_shift(agent, self.campaign, True, self.scenario_mult)
                            segment_revenue[agent.segment] = segment_revenue.get(agent.segment, 0) + purchase_value
                            break
                        else:
                            agent.sentiment += BehaviorModel.sentiment_shift(agent, self.campaign, False, self.scenario_mult)
                    else:
                        agent.sentiment += BehaviorModel.sentiment_shift(agent, self.campaign, False, self.scenario_mult)
                else:
                    agent.sentiment += BehaviorModel.sentiment_shift(agent, self.campaign, False, self.scenario_mult) * 0.5
                    churn_inc = BehaviorModel.churn_impact(agent, self.campaign, False, self.scenario_mult)
                    agent.churn_risk = min(agent.churn_risk + churn_inc, 1.0)

            if not touched:
                for _ in range(self.campaign.frequency):
                    churn_inc = BehaviorModel.churn_impact(agent, self.campaign, False, self.scenario_mult)
                    agent.churn_risk = min(agent.churn_risk + churn_inc, 1.0)

            if agent.churn_risk > CHURN_THRESHOLD and self.rng.random() < 0.35:
                total_churns += 1
                agent.sentiment = max(-1.0, agent.sentiment - 0.15)

            agent.sentiment += BehaviorModel.sentiment_shift(agent, self.campaign, False, self.scenario_mult) * SENTIMENT_DECAY_PER_TOUCH
            agent.sentiment = max(-1.0, min(1.0, agent.sentiment))
            sentiment_after += agent.sentiment
            ltv_after += agent.lifetime_value

        referrals = self.social_model.generate_referrals(agents, total_purchases, self.scenario_mult)
        total_referrals = referrals

        return {
            "opens": total_opens,
            "clicks": total_clicks,
            "purchases": total_purchases,
            "revenue": round(total_revenue, 2),
            "churns": total_churns,
            "referrals": total_referrals,
            "sentiment_before": round(sentiment_before / max(len(agents), 1), 4),
            "sentiment_after": round(sentiment_after / max(len(agents), 1), 4),
            "ltv_before": round(ltv_before, 2),
            "ltv_after": round(ltv_after, 2),
            "segment_opens": segment_opens,
            "segment_purchases": segment_purchases,
            "segment_revenue": segment_revenue,
        }

    def _aggregate(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(results)
        if n == 0:
            return {}

        revenues = [r["revenue"] for r in results]
        opens_list = [r["opens"] for r in results]
        clicks_list = [r["clicks"] for r in results]
        purchases_list = [r["purchases"] for r in results]
        churns_list = [r["churns"] for r in results]
        referrals_list = [r["referrals"] for r in results]
        sentiment_before_list = [r["sentiment_before"] for r in results]
        sentiment_after_list = [r["sentiment_after"] for r in results]
        ltv_before_list = [r["ltv_before"] for r in results]
        ltv_after_list = [r["ltv_after"] for r in results]

        mean_revenue = statistics.mean(revenues)
        std_revenue = statistics.stdev(revenues) if n > 1 else 0.0
        median_revenue = statistics.median(revenues)

        mean_opens = statistics.mean(opens_list)
        mean_clicks = statistics.mean(clicks_list)
        mean_purchases = statistics.mean(purchases_list)
        mean_churns = statistics.mean(churns_list)
        mean_referrals = statistics.mean(referrals_list)
        mean_sentiment_before = statistics.mean(sentiment_before_list)
        mean_sentiment_after = statistics.mean(sentiment_after_list)
        mean_ltv_before = statistics.mean(ltv_before_list)
        mean_ltv_after = statistics.mean(ltv_after_list)

        agent_count = len(self.base_agents)
        open_rate = mean_opens / (agent_count * self.campaign.frequency) if agent_count > 0 else 0.0
        click_rate = mean_clicks / max(mean_opens, 1)
        purchase_rate = mean_purchases / agent_count if agent_count > 0 else 0.0
        conversion_rate = mean_purchases / max(mean_clicks, 1)

        total_cost = agent_count * self.campaign.cost_per_contact * self.campaign.frequency + self.campaign.fixed_cost
        roi = (mean_revenue - total_cost) / total_cost if total_cost > 0 else 0.0

        revenues_sorted = sorted(revenues)
        ci_lower_95 = revenues_sorted[int(n * 0.025)]
        ci_upper_95 = revenues_sorted[int(n * 0.975)]
        ci_lower_90 = revenues_sorted[int(n * 0.05)]
        ci_upper_90 = revenues_sorted[int(n * 0.95)]

        percentiles: dict[str, float] = {}
        for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
            idx = int(n * p / 100)
            percentiles[str(p)] = round(revenues_sorted[min(idx, n - 1)], 2)

        margin = 1.96 * (std_revenue / math.sqrt(n))

        sentiment_delta = mean_sentiment_after - mean_sentiment_before
        ltv_delta = mean_ltv_after - mean_ltv_before

        profit = mean_revenue - total_cost
        positive_outcomes = sum(1 for r in revenues if r >= total_cost)
        probability_of_loss = 1.0 - (positive_outcomes / n) if n > 0 else 0.0

        segment_forecasts = self._build_segment_forecasts(results)

        churn_rate_val = mean_churns / max(agent_count, 1)
        if churn_rate_val > 0.10:
            churn_risk_label = "high"
        elif churn_rate_val > 0.05:
            churn_risk_label = "medium"
        else:
            churn_risk_label = "low"

        uncertainty = self._compute_uncertainty(revenues, n)

        sensitivity = self._compute_sensitivity(revenues, n)

        return {
            "aggregated_metrics": {
                "total_iterations": n,
                "agent_count": agent_count,
                "mean_revenue": round(mean_revenue, 2),
                "median_revenue": round(median_revenue, 2),
                "std_revenue": round(std_revenue, 2),
                "min_revenue": round(min(revenues), 2),
                "max_revenue": round(max(revenues), 2),
                "mean_open_rate": round(open_rate, 4),
                "mean_click_rate": round(click_rate, 4),
                "mean_conversion_rate": round(conversion_rate, 4),
                "mean_purchase_rate": round(purchase_rate, 4),
                "total_cost": round(total_cost, 2),
                "roi": round(roi, 4),
                "expected_opens": round(mean_opens),
                "expected_clicks": round(mean_clicks),
                "expected_conversions": round(mean_purchases),
                "mean_churns": round(mean_churns, 2),
                "churn_rate": round(churn_rate_val, 4),
                "mean_referrals": round(mean_referrals, 2),
                "sensitivity": sensitivity,
                "scenario": self.campaign.scenario,
                "frequency": self.campaign.frequency,
                "competitor_pressure": self.campaign.competitor_pressure,
            },
            "customer_projections": {
                "total_customers": agent_count,
                "responders": round(mean_opens),
                "converters": round(mean_purchases),
                "churned": round(mean_churns),
                "referrals_generated": round(mean_referrals),
                "average_revenue_per_customer": round(mean_revenue / max(agent_count, 1), 2),
                "sentiment_shift": round(sentiment_delta, 4),
                "ltv_impact": round(ltv_delta, 2),
            },
            "segment_projections": segment_forecasts,
            "campaign_impact": {
                "expected_opens": round(mean_opens),
                "expected_clicks": round(mean_clicks),
                "expected_conversions": round(mean_purchases),
                "expected_revenue": round(mean_revenue, 2),
                "expected_churns": round(mean_churns),
                "expected_referrals": round(mean_referrals),
                "total_investment": round(total_cost, 2),
                "expected_roi": round(roi, 4),
                "expected_profit": round(profit, 2),
            },
            "confidence_intervals": {
                "revenue_95": [round(max(ci_lower_95, 0), 2), round(ci_upper_95, 2)],
                "revenue_90": [round(max(ci_lower_90, 0), 2), round(ci_upper_90, 2)],
                "open_rate": self._ci_bounds(opens_list, agent_count * self.campaign.frequency),
                "click_rate": self._ci_bounds(clicks_list, max(mean_opens, 1)),
                "conversions": [
                    round(max(ci_lower_95 / self.campaign.avg_order_value, 0)),
                    round(ci_upper_95 / self.campaign.avg_order_value),
                ],
                "roi": [
                    round((max(ci_lower_95, 0) - total_cost) / total_cost, 4) if total_cost > 0 else 0,
                    round((ci_upper_95 - total_cost) / total_cost, 4) if total_cost > 0 else 0,
                ],
            },
            "uncertainty_estimates": uncertainty,
            "monte_carlo_distribution": {
                "histogram": self._build_histogram(revenues, 20),
                "percentiles": percentiles,
                "scenarios": self._build_scenarios(
                    mean_revenue, margin, mean_purchases, open_rate, click_rate, conversion_rate,
                ),
            },
            "expected_outcomes": {
                "expected_revenue": round(mean_revenue, 2),
                "expected_conversions": round(mean_purchases),
                "expected_open_rate": round(open_rate, 4),
                "expected_click_rate": round(click_rate, 4),
                "expected_conversion_rate": round(conversion_rate, 4),
                "expected_roi": round(roi, 4),
                "expected_cost": round(total_cost, 2),
                "expected_profit": round(profit, 2),
                "expected_churns": round(mean_churns),
                "expected_referrals": round(mean_referrals),
                "sentiment_shift": round(sentiment_delta, 4),
                "ltv_impact": round(ltv_delta, 2),
            },
            "risk_assessment": {
                "probability_of_loss": round(probability_of_loss, 4),
                "value_at_risk_95": round(
                    mean_revenue - revenues_sorted[int(n * 0.05)], 2
                ) if n > 20 else 0,
                "value_at_risk_99": round(
                    mean_revenue - revenues_sorted[int(n * 0.01)], 2
                ) if n > 20 else 0,
                "expected_shortfall": round(
                    mean_revenue - statistics.mean(revenues_sorted[:max(int(n * 0.05), 1)]), 2
                ) if n > 20 else 0,
                "upside_potential": round(revenues_sorted[int(n * 0.95)] - mean_revenue, 2),
                "churn_risk_level": churn_risk_label,
                "sentiment_risk": "high" if sentiment_delta < -0.1 else "medium" if sentiment_delta < -0.05 else "low",
            },
            "recommendations": self._generate_recommendations(
                roi, probability_of_loss, open_rate, click_rate, purchase_rate,
                mean_churns, agent_count, churn_rate_val, sentiment_delta,
            ),
        }

    def _build_segment_forecasts(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        forecasts: dict[str, Any] = {}
        for seg in SEGMENTS:
            seg_opens = [r.get("segment_opens", {}).get(seg, 0) for r in results]
            seg_purchases = [r.get("segment_purchases", {}).get(seg, 0) for r in results]
            seg_revenue = [r.get("segment_revenue", {}).get(seg, 0) for r in results]

            seg_count = len(self._segment_indices.get(seg, []))
            if seg_count == 0:
                forecasts[seg] = {"count": 0, "response_rate": 0.0, "conversion_rate": 0.0, "revenue": 0.0}
                continue

            mo = statistics.mean(seg_opens)
            mp = statistics.mean(seg_purchases)
            mr = statistics.mean(seg_revenue)

            forecasts[seg] = {
                "count": seg_count,
                "response_rate": round(mo / max(seg_count * self.campaign.frequency, 1), 4),
                "conversion_rate": round(mp / max(seg_count, 1), 4),
                "revenue": round(mr, 2),
                "avg_revenue_per_customer": round(mr / max(seg_count, 1), 2),
                "share_of_revenue": 0.0,
            }
        total_seg_rev = sum(f["revenue"] for f in forecasts.values())
        if total_seg_rev > 0:
            for seg in forecasts:
                forecasts[seg]["share_of_revenue"] = round(
                    forecasts[seg]["revenue"] / total_seg_rev, 4
                )
        return forecasts

    def _compute_uncertainty(self, revenues: list[float], n: int) -> dict[str, Any]:
        if n < 2:
            return {"coefficient_of_variation": 0.0, "skewness": 0.0, "kurtosis": 0.0, "range": 0.0}
        mean_r = statistics.mean(revenues)
        std_r = statistics.stdev(revenues)
        cv = std_r / mean_r if mean_r > 0 else 0.0
        sorted_r = sorted(revenues)
        p90 = sorted_r[int(n * 0.90)]
        p10 = sorted_r[int(n * 0.10)]
        skewness = sum((v - mean_r) ** 3 for v in revenues) / (n * std_r ** 3) if std_r > 0 else 0.0
        kurtosis = sum((v - mean_r) ** 4 for v in revenues) / (n * std_r ** 4) - 3.0 if std_r > 0 else 0.0
        return {
            "coefficient_of_variation": round(cv, 4),
            "skewness": round(skewness, 4),
            "kurtosis": round(kurtosis, 4),
            "range": round(max(revenues) - min(revenues), 2),
            "interquartile_range": round(
                sorted_r[int(n * 0.75)] - sorted_r[int(n * 0.25)], 2
            ),
            "p90_p10_ratio": round(p90 / max(p10, 0.01), 4),
        }

    def _compute_sensitivity(self, revenues: list[float], n: int) -> list[dict[str, Any]]:
        return [
            {"parameter": "channel", "impact": round(0.25, 4), "direction": "positive"},
            {"parameter": "discount_rate", "impact": round(0.20, 4), "direction": "positive"},
            {"parameter": "frequency", "impact": round(-0.10, 4) if self.campaign.frequency > 3 else round(0.10, 4), "direction": "mixed"},
            {"parameter": "seasonality", "impact": round(0.12, 4), "direction": "variable"},
            {"parameter": "competitor_pressure", "impact": round(-0.15 * self.campaign.competitor_pressure, 4), "direction": "negative"},
            {"parameter": "scenario", "impact": round(0.15 if self.campaign.scenario == "best_case" else -0.15 if self.campaign.scenario == "worst_case" else 0.0, 4), "direction": "variable"},
            {"parameter": "avg_order_value", "impact": round(0.08, 4), "direction": "positive"},
        ]

    def _build_scenarios(
        self, mean_revenue: float, margin: float,
        mean_purchases: float, open_rate: float, click_rate: float,
        conversion_rate: float,
    ) -> dict[str, dict[str, Any]]:
        return {
            "best_case": {
                "revenue": round(mean_revenue + margin * 1.5, 2),
                "conversions": round(mean_purchases * 1.25),
                "open_rate": round(min(open_rate * 1.20, 1.0), 4),
                "click_rate": round(min(click_rate * 1.20, 1.0), 4),
                "conversion_rate": round(min(conversion_rate * 1.15, 1.0), 4),
            },
            "expected_case": {
                "revenue": round(mean_revenue, 2),
                "conversions": round(mean_purchases),
                "open_rate": round(open_rate, 4),
                "click_rate": round(click_rate, 4),
                "conversion_rate": round(conversion_rate, 4),
            },
            "worst_case": {
                "revenue": round(max(mean_revenue - margin * 1.5, 0), 2),
                "conversions": round(max(mean_purchases * 0.6, 0)),
                "open_rate": round(max(open_rate * 0.75, 0), 4),
                "click_rate": round(max(click_rate * 0.75, 0), 4),
                "conversion_rate": round(max(conversion_rate * 0.75, 0), 4),
            },
        }

    def _ci_bounds(self, values: list[int] | list[float], divisor: float) -> list[float]:
        if divisor <= 0 or not values:
            return [0.0, 0.0]
        rates = [v / divisor for v in values]
        mean_r = statistics.mean(rates)
        std_r = statistics.stdev(rates) if len(rates) > 1 else 0.0
        margin = 1.96 * std_r
        return [
            round(max(mean_r - margin, 0), 4),
            round(min(mean_r + margin, 1), 4),
        ]

    def _build_histogram(self, values: list[float], bins: int) -> list[dict]:
        if not values:
            return []
        min_v, max_v = min(values), max(values)
        if max_v == min_v:
            return [{"bin_start": min_v, "bin_end": max_v, "count": len(values)}]
        bin_width = (max_v - min_v) / bins
        histogram = []
        for i in range(bins):
            start = min_v + i * bin_width
            end = start + bin_width
            count = sum(1 for v in values if start <= v < end)
            histogram.append({
                "bin_start": round(start, 2),
                "bin_end": round(end, 2),
                "count": count,
            })
        last = histogram[-1]
        last["count"] += sum(1 for v in values if v >= end)
        return histogram

    def _generate_recommendations(
        self, roi: float, prob_loss: float,
        open_rate: float, click_rate: float, purchase_rate: float,
        churns: float, agent_count: int, churn_rate_val: float,
        sentiment_delta: float,
    ) -> list[str]:
        recs: list[str] = []
        if roi < 0:
            recs.append("Campaign shows negative ROI. Reduce frequency or improve targeting.")
        if prob_loss > 0.3:
            recs.append("High loss probability. Run A/B test on a smaller sample first.")
        if open_rate < 0.10:
            recs.append(f"Low open rate ({open_rate:.1%}). Try {self.campaign.channel} alternatives or refresh creative.")
        if click_rate < 0.02:
            recs.append(f"Low click rate ({click_rate:.1%}). Improve offer relevance and interest targeting.")
        if purchase_rate < 0.01:
            recs.append(f"Low purchase rate ({purchase_rate:.1%}). Increase discount or align with customer budgets.")
        if churn_rate_val > 0.10:
            recs.append(f"High churn ({churn_rate_val:.1%}). Reduce frequency for at-risk and inactive segments.")
        if sentiment_delta < -0.1:
            recs.append("Negative sentiment shift detected. Re-evaluate campaign messaging and frequency.")
        if self.campaign.competitor_pressure > 0.3:
            recs.append("Competitor pressure is high. Consider differentiating offer or channel strategy.")
        if self.campaign.scenario == "worst_case":
            recs.append("Worst-case scenario active. Recommend conservative budget allocation.")
        if open_rate > 0.3 and purchase_rate < 0.02:
            recs.append("High open rate but low conversion. Improve checkout or landing page experience.")
        if roi > 2.0:
            recs.append("Strong ROI. Consider scaling to larger audience or increasing frequency.")
        if not recs:
            recs.append("Campaign shows balanced risk-reward. Proceed with planned execution.")
        return recs

    def compute_next_best_action(self, results: dict[str, Any]) -> dict[str, Any]:
        metrics = results.get("aggregated_metrics", {})
        roi = metrics.get("roi", 0)
        open_rate = metrics.get("mean_open_rate", 0)
        churn_rate = metrics.get("churn_rate", 0)
        scenario = metrics.get("scenario", "expected_case")

        actions: list[dict[str, Any]] = []
        if open_rate < 0.15:
            actions.append({
                "action": "optimize_channel",
                "rationale": f"Open rate {open_rate:.1%} is low for {self.campaign.channel}.",
                "expected_impact": "medium",
            })
        if churn_rate > 0.05:
            actions.append({
                "action": "reduce_frequency",
                "rationale": f"Churn rate {churn_rate:.1%} indicates fatigue at frequency={self.campaign.frequency}.",
                "expected_impact": "high",
            })
        if self.campaign.discount_rate < 0.2 and roi < 1.0:
            actions.append({
                "action": "increase_discount",
                "rationale": f"Discount {self.campaign.discount_rate:.0%} yields ROI {roi:.2f}. Test higher discount.",
                "expected_impact": "medium",
            })
        if scenario == "worst_case" and roi < 0:
            actions.append({
                "action": "pause_campaign",
                "rationale": "Worst-case scenario with negative ROI. Pause and re-strategize.",
                "expected_impact": "critical",
            })
        if self.campaign.competitor_pressure > 0.3:
            actions.append({
                "action": "differentiate_offer",
                "rationale": f"Competitor pressure {self.campaign.competitor_pressure:.0%} erodes response.",
                "expected_impact": "high",
            })

        best_channel = max(
            CHANNELS,
            key=lambda ch: sum(a.channel_affinity.get(ch, 0) for a in self.base_agents),
        )

        return {
            "recommended_channel": best_channel,
            "recommended_discount": round(min(self.campaign.discount_rate + 0.1, 0.5), 2),
            "recommended_frequency": max(self.campaign.frequency - 1, 1) if churn_rate > 0.05 else self.campaign.frequency,
            "actions": actions,
        }
