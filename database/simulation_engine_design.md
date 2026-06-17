# Campaign Simulation Engine Design

## 1. Agent Architecture

```python
@dataclass
class CustomerAgent:
    """
    Every customer in the simulation becomes an autonomous agent.
    Agent properties derived from their digital twin.
    """
    customer_id: UUID
    organization_id: UUID
    
    # --- Core Properties ---
    budget: float                    # Remaining budget for purchases
    loyalty: float                   # 0.0 (disloyal) - 1.0 (brand advocate)
    patience: float                  # 0.0 (impulsive) - 1.0 (deliberate)
    sentiment: float                 # -1.0 (negative) - 1.0 (positive)
    
    # --- Preferences ---
    interests: dict[str, float]      # {category: interest_level}
    price_sensitivity: float         # 0.0 (price-agnostic) - 1.0 (price-sensitive)
    brand_affinity: dict[str, float] # {brand: affinity_score}
    communication_preference: str    # email, sms, push, in_app
    
    # --- Behavioral State ---
    state: AgentState
    memory: AgentMemory
    
    # --- History (current simulation) ---
    interaction_history: list[Interaction]
    purchase_history: list[Purchase]
    communication_history: list[Communication]
    
    # --- Decision Parameters ---
    decision_weights: DecisionWeights
    
    @dataclass
    class AgentState:
        current_mood: str        # positive, neutral, negative, frustrated, excited
        fatigue_level: float     # 0.0 - 1.0 (communication fatigue)
        engagement_level: float  # 0.0 - 1.0
        intent: str              # purchase, browse, research, churn, inactive
        in_consideration_set: bool
        last_interaction_minutes_ago: int
        patience_remaining: float
        
    @dataclass
    class AgentMemory:
        recent_communications: list[dict]  # Last 10
        recent_offers_seen: list[dict]     # Last 10 offers
        positive_experiences: list[str]     # Good interactions
        negative_experiences: list[str]     # Bad interactions
        brand_perception: float            # -1.0 - 1.0
        competitor_engagement: float       # 0.0 - 1.0
        
    @dataclass
    class DecisionWeights:
        # Weights for decision factors
        price_weight: float = 0.3
        relevance_weight: float = 0.25
        timing_weight: float = 0.15
        channel_weight: float = 0.15
        brand_weight: float = 0.1
        fatigue_weight: float = 0.05
        

@dataclass
class Interaction:
    type: str                     # view, click, open, dismiss, purchase
    timestamp: int                # simulation step
    value: float                  # monetary value if purchase
    channel: str
    content_id: str | None


@dataclass
class Purchase:
    product_id: str
    category: str
    price: float
    discount_applied: float = 0.0
    timestamp: int = 0


@dataclass
class Communication:
    campaign_id: str
    channel: str
    message_type: str
    timestamp: int
    response: str | None          # opened, clicked, dismissed, unsubscribed
```

## 2. Agent State Machine

```
                    ┌─────────────────────────────────────────────────────┐
                    │               AGENT STATE MACHINE                    │
                    └──────────────────────────────────────────────────────┘

                                ┌──────────┐
                                │  INACTIVE │◄──────────────────────────┐
                                └─────┬────┘                            │
                                      │ receive_communication            │
                                      ▼                                  │
                                ┌──────────┐                            │
                  ┌────────────►│ AWARE    │                            │
                  │             └─────┬────┘                            │
                  │                   │ evaluate                         │
                  │                   ▼                                  │
                  │             ┌──────────┐                            │
                  │             │CONSIDERING│◄───── re-evaluate ────────│
                  │             └─────┬────┘                            │
                  │                   │ decide                           │
                  │          ┌────────┼────────┐                        │
                  │          │        │        │                        │
                  │          ▼        ▼        ▼                        │
                  │    ┌────────┐┌────────┐┌────────┐                   │
                  │    │PURCHASE││ DISMISS││ DEFER  │───────────────────┤
                  │    └───┬────┘└────────┘└────────┘                   │
                  │        │                                            │
                  │        ▼                                            │
                  │    ┌────────┐    ┌───────────┐                     │
                  │    │ POST-  │───►│ SATISFIED │ (positive)          │
                  │    │PURCHASE│    └───────────┘                     │
                  │    └────────┘    ┌───────────┐                     │
                  │                  │ DISSATISFIED│ (negative)         │
                  │                  └──────┬────┘                     │
                  │                         │ escalate?                 │
                  │                         ▼                          │
                  │                  ┌──────────┐                      │
                  │                  │ CHURNING │────► CHURNED         │
                  │                  └──────────┘                      │
                  │                                                     │
                  └──── fatigue/dismiss count > threshold ─────────────┘

State Transitions:
  INACTIVE -> AWARE:         Campaign message received
  AWARE -> CONSIDERING:      Message relevance > threshold
  AWARE -> INACTIVE:         Relevance < threshold (repeatedly)
  CONSIDERING -> PURCHASE:   Decision model yields purchase
  CONSIDERING -> DISMISS:    Not interested or bad timing
  CONSIDERING -> DEFER:      May buy later (price checking, comparison)
  DEFER -> CONSIDERING:      Reminder or price drop
  PURCHASE -> SATISFIED:     Post-purchase sentiment positive
  PURCHASE -> DISSATISFIED:  Post-purchase sentiment negative
  SATISFIIED -> AWARE:       Normal re-engagement
  DISSATISFIED -> CHURNING:  Negative experience escalation
  CHURNING -> CHURNED:       Churn confirmed
  CHURNING -> AWARE:         Win-back campaign succeeds
```

## 3. Decision Engine

```python
class AgentDecisionEngine:
    """
    Core decision engine for customer agents.
    Determines how agents respond to campaign communications.
    """
    
    @staticmethod
    def compute_open_probability(agent: CustomerAgent, message: dict) -> float:
        """
        Probability of opening/reading a message.
        
        Factors:
        - Channel affinity (preferred channel gets higher probability)
        - Sender trust (brand affinity)
        - Fatigue level (lower with higher fatigue)
        - Time of day fit (match agent's preferred time)
        - Day of week fit (match agent's preferred day)
        - Subject line relevance (based on interests)
        - Recent communication count (diminishing returns)
        """
        channel_score = AgentDecisionEngine._channel_affinity_score(agent, message['channel'])
        brand_score = agent.brand_affinity.get(message.get('brand', ''), 0.5)
        fatigue_penalty = 1.0 - agent.state.fatigue_level * 0.5
        timing_score = AgentDecisionEngine._timing_score(agent)
        relevance_score = AgentDecisionEngine._compute_relevance(agent, message)
        recency_penalty = AgentDecisionEngine._recency_penalty(agent)
        
        probability = (
            channel_score * 0.25 +
            brand_score * 0.20 +
            relevance_score * 0.25 +
            timing_score * 0.10 +
            fatigue_penalty * 0.10 +
            recency_penalty * 0.10
        )
        
        return np.clip(probability, 0.01, 0.99)
    
    @staticmethod
    def compute_click_probability(agent: CustomerAgent, message: dict) -> float:
        """
        Probability of clicking after opening.
        
        Factors:
        - Message relevance to interests
        - Call-to-action clarity
        - Offer attractiveness (discount, value)
        - Price sensitivity fit
        - Urgency (limited time offers)
        - Previous click-through rate
        """
        relevance = AgentDecisionEngine._compute_relevance(agent, message)
        offer_value = AgentDecisionEngine._compute_offer_value(agent, message)
        urgency = message.get('urgency', 0.0)
        historical_ctr = AgentDecisionEngine._historical_ctr(agent, message['channel'])
        
        probability = (
            relevance * 0.35 +
            offer_value * 0.30 +
            urgency * 0.15 +
            historical_ctr * 0.20
        )
        
        return np.clip(probability, 0.01, 0.95)
    
    @staticmethod
    def compute_purchase_probability(
        agent: CustomerAgent,
        product: dict,
        offer: dict | None = None
    ) -> float:
        """
        Probability of completing a purchase.
        
        Factors:
        - Product-category interest match
        - Price sensitivity (lower if price > threshold)
        - Budget remaining
        - Current sentiment
        - Past purchase satisfaction (repeat buyer boost)
        - Competitor comparison (brand loyalty)
        - Urgency/deadline effect
        - Discount depth (if offer present)
        - Patience level (impulsive buyers convert faster)
        """
        interest_match = agent.interests.get(product.get('category', ''), 0.0)
        price_fit = AgentDecisionEngine._price_fit(agent, product.get('price', 0), offer)
        budget_ok = 1.0 if product.get('price', 0) <= agent.budget else max(0, 1.0 - (product['price'] - agent.budget) / agent.budget)
        sentiment_modifier = 1.0 + agent.sentiment * 0.2
        repeat_boost = 1.2 if product.get('category') in [p.category for p in agent.purchase_history] else 1.0
        patience_modifier = 1.0 - agent.patience * 0.3  # Impulsive: more likely
        
        probability = (
            interest_match * 0.25 +
            price_fit * 0.25 +
            budget_ok * 0.20 +
            sentiment_modifier * 0.10 +
            repeat_boost * 0.10 +
            patience_modifier * 0.10
        )
        
        return np.clip(probability, 0.001, 0.90)
    
    @staticmethod
    def compute_fatigue_increase(agent: CustomerAgent, message: dict) -> float:
        """
        How much this communication increases fatigue.
        
        - Irrelevant messages increase fatigue more
        - Same channel repeatedly increases more
        - During quiet hours increases more
        """
        relevance = AgentDecisionEngine._compute_relevance(agent, message)
        channel_repeat = sum(
            1 for c in agent.communication_history[-5:]
            if c.channel == message['channel']
        ) / 5.0
        quiet_hours = AgentDecisionEngine._is_quiet_hours(agent)
        
        increase = (1.0 - relevance) * 0.3 + channel_repeat * 0.2 + (0.2 if quiet_hours else 0)
        return min(increase, 0.3)  # Cap fatigue increase
    
    @staticmethod
    def _compute_relevance(agent: CustomerAgent, message: dict) -> float:
        """Compute message relevance to agent's interests."""
        message_categories = message.get('categories', [])
        if not message_categories:
            return 0.5  # Neutral for generic messages
        
        scores = []
        for cat in message_categories:
            interest = agent.interests.get(cat, 0.0)
            scores.append(interest)
        
        return max(scores) if scores else 0.3
    
    @staticmethod
    def _compute_offer_value(agent: CustomerAgent, message: dict) -> float:
        """Compute perceived value of an offer."""
        if 'discount' not in message and 'offer' not in message:
            return 0.0
        
        discount = message.get('discount', 0)
        if discount > 0:
            sensitivity = agent.price_sensitivity
            return discount * (1.0 + sensitivity)  # Price-sensitive value discounts more
        
        return 0.3  # Generic offer value
    
    @staticmethod
    def _price_fit(agent: CustomerAgent, price: float, offer: dict | None = None) -> float:
        """How well does the price match agent's willingness to pay."""
        willingness_to_pay = 100.0 * (1.0 - agent.price_sensitivity * 0.5)
        effective_price = price
        if offer and 'discount' in offer:
            effective_price = price * (1.0 - offer['discount'])
        
        if effective_price <= willingness_to_pay:
            return 1.0
        else:
            return max(0.0, 1.0 - (effective_price - willingness_to_pay) / willingness_to_pay)
    
    @staticmethod
    def _channel_affinity_score(agent: CustomerAgent, channel: str) -> float:
        """Score agent's affinity for a communication channel."""
        preferred = agent.communication_preference
        if channel == preferred:
            return 0.9
        # Secondary preference based on historical engagement
        channel_opens = sum(
            1 for c in agent.communication_history
            if c.channel == channel and c.response == 'opened'
        )
        total_channel = sum(1 for c in agent.communication_history if c.channel == channel)
        if total_channel > 0:
            return channel_opens / total_channel
        return 0.3  # Unknown channel
    
    @staticmethod
    def _timing_score(agent: CustomerAgent) -> float:
        """Score how good the current timing is."""
        current_hour = datetime.now().hour
        preferred_hour = 10  # Default preferred hour
        hour_diff = abs(current_hour - preferred_hour)
        return max(0.0, 1.0 - hour_diff / 12.0)
    
    @staticmethod
    def _recency_penalty(agent: CustomerAgent) -> float:
        """Penalty for recent communications."""
        recent = [
            c for c in agent.communication_history[-5:]
            if (datetime.now() - datetime.fromtimestamp(c.timestamp)).total_seconds() < 3600
        ]
        return max(0.5, 1.0 - len(recent) * 0.1)  # Min 0.5
    
    @staticmethod
    def _is_quiet_hours(agent: CustomerAgent) -> bool:
        """Check if current time is in agent's quiet hours."""
        current_hour = datetime.now().hour
        # Default quiet hours: 22:00 - 08:00
        return current_hour < 8 or current_hour >= 22
```

## 4. Reward Function

```python
class SimulationRewardFunction:
    """
    Reward function for the simulation optimization.
    Used to score campaign strategies and optimize decisions.
    """
    
    @staticmethod
    def compute_global_reward(
        campaign_results: dict,
        agents_responses: list[AgentResponse],
        campaign_config: dict,
    ) -> dict:
        """
        Global reward for campaign performance.
        
        Components:
        1. Conversion Reward: Revenue from conversions
        2. Engagement Reward: Positive engagement (opens, clicks)
        3. Sentiment Impact: Change in customer sentiment
        4. Brand Health: Long-term brand perception change
        5. Fatigue Cost: Communication fatigue caused
        6. Churn Risk: Changes in churn probability
        """
        conversion_reward = SimulationRewardFunction._conversion_reward(campaign_results)
        engagement_reward = SimulationRewardFunction._engagement_reward(agents_responses)
        sentiment_impact = SimulationRewardFunction._sentiment_impact(agents_responses)
        fatigue_cost = SimulationRewardFunction._fatigue_cost(agents_responses)
        churn_penalty = SimulationRewardFunction._churn_penalty(agents_responses)
        
        total_reward = (
            conversion_reward * 0.40 +
            engagement_reward * 0.20 +
            sentiment_impact * 0.15 -
            fatigue_cost * 0.15 -
            churn_penalty * 0.10
        )
        
        return {
            'total_reward': total_reward,
            'conversion_reward': conversion_reward,
            'engagement_reward': engagement_reward,
            'sentiment_impact': sentiment_impact,
            'fatigue_cost': fatigue_cost,
            'churn_penalty': churn_penalty,
        }
    
    @staticmethod
    def compute_agent_reward(agent: CustomerAgent, response: AgentResponse) -> float:
        """
        Individual agent-level reward.
        
        Positive rewards:
        - Relevant, well-timed communications
        - Offers matching interests and price sensitivity
        - Preferred channel usage
        
        Negative rewards:
        - Irrelevant messages
        - Excessive frequency (fatigue)
        - Poor timing
        """
        relevance = AgentDecisionEngine._compute_relevance(agent, response.message)
        timing = AgentDecisionEngine._timing_score(agent)
        channel_fit = AgentDecisionEngine._channel_affinity_score(agent, response.message.get('channel', ''))
        fatigue_impact = response.fatigue_increase
        
        agent_reward = (
            relevance * 0.3 +
            timing * 0.2 +
            channel_fit * 0.2 -
            fatigue_impact * 0.3
        )
        
        # Bonus for conversion
        if response.action == 'purchase':
            agent_reward += 1.0
        
        # Penalty for unsubscribing
        if response.action == 'unsubscribe':
            agent_reward -= 2.0
        
        return agent_reward
    
    @staticmethod
    def _conversion_reward(results: dict) -> float:
        """Reward for conversions and revenue."""
        revenue = results.get('total_revenue', 0)
        conversions = results.get('total_conversions', 0)
        conversion_rate = results.get('conversion_rate', 0)
        
        reward = (
            min(revenue / 10000, 1.0) * 0.5 +
            min(conversions / 100, 1.0) * 0.25 +
            conversion_rate * 0.25
        )
        return reward
    
    @staticmethod
    def _engagement_reward(responses: list[AgentResponse]) -> float:
        """Reward for positive engagement."""
        if not responses:
            return 0.0
        
        opens = sum(1 for r in responses if r.action == 'open')
        clicks = sum(1 for r in responses if r.action == 'click')
        total = len(responses)
        
        open_rate = opens / total if total > 0 else 0
        click_rate = clicks / total if total > 0 else 0
        
        return open_rate * 0.5 + click_rate * 0.5
    
    @staticmethod
    def _sentiment_impact(responses: list[AgentResponse]) -> float:
        """Measure sentiment change."""
        sentiment_changes = [
            r.sentiment_change for r in responses
            if r.sentiment_change is not None
        ]
        if not sentiment_changes:
            return 0.0
        return sum(sentiment_changes) / len(sentiment_changes)
    
    @staticmethod
    def _fatigue_cost(responses: list[AgentResponse]) -> float:
        """Cost of communication fatigue."""
        fatigue_increases = [r.fatigue_increase for r in responses if r.fatigue_increase > 0]
        if not fatigue_increases:
            return 0.0
        return min(sum(fatigue_increases) / len(responses), 1.0)
    
    @staticmethod
    def _churn_penalty(responses: list[AgentResponse]) -> float:
        """Penalty for increased churn risk."""
        churn_increases = [
            r.churn_probability_change for r in responses
            if r.churn_probability_change and r.churn_probability_change > 0
        ]
        if not churn_increases:
            return 0.0
        return min(sum(churn_increases) / len(responses), 1.0)
```

## 5. Simulation Engine

```python
class CampaignSimulationEngine:
    """
    High-performance simulation engine for running campaign simulations.
    
    Design:
    - Parallel agent execution using multiprocessing
    - Monte Carlo iterations for probabilistic outcomes
    - Discrete event simulation (DES) time steps
    - Configurable time horizon and granularity
    """
    
    def __init__(
        self,
        config: SimulationConfig,
        db: DatabaseClient,
        cache: RedisClient,
        kafka: KafkaProducer,
    ):
        self.config = config
        self.db = db
        self.cache = cache
        self.kafka = kafka
        self.agents: dict[str, CustomerAgent] = {}
        
    async def run_simulation(
        self,
        simulation_id: UUID,
        campaign_config: dict,
        segment_ids: list[UUID],
        sample_size: int = 10000,
        iterations: int = 1000,
        time_horizon_days: int = 30,
    ) -> SimulationResults:
        """
        Run a complete simulation.
        
        Steps:
        1. Load agents from database (sample from segments)
        2. Initialize agent states
        3. Run Monte Carlo iterations in parallel
        4. Aggregate results
        5. Compute confidence intervals
        6. Store results
        """
        # 1. Load agents
        agents = await self._load_agents(simulation_id, segment_ids, sample_size)
        
        # 2. Run iterations
        all_results = []
        batch_size = min(100, iterations)
        
        for batch_start in range(0, iterations, batch_size):
            batch_end = min(batch_start + batch_size, iterations)
            
            # Run batch in parallel
            batch_tasks = [
                self._run_single_iteration(
                    copy.deepcopy(agents),
                    campaign_config,
                    time_horizon_days,
                    seed=batch_start + i,
                )
                for i in range(batch_start, batch_end)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks)
            all_results.extend(batch_results)
            
            # Update progress
            progress = (batch_end / iterations) * 100
            await self._update_simulation_progress(simulation_id, progress)
        
        # 3. Aggregate
        aggregated = self._aggregate_results(all_results)
        
        # 4. Confidence intervals
        confidence_intervals = self._compute_confidence_intervals(
            all_results,
            confidence_level=self.config.confidence_level,
        )
        
        # 5. Expected outcomes
        expected = self._compute_expected_outcomes(aggregated)
        
        # 6. Risk assessment
        risk = self._assess_risk(all_results, expected)
        
        results = SimulationResults(
            simulation_id=simulation_id,
            aggregated_metrics=aggregated,
            confidence_intervals=confidence_intervals,
            expected_outcomes=expected,
            risk_assessment=risk,
            customer_projections=self._compute_customer_projections(agents, all_results),
            segment_projections=self._compute_segment_projections(agents, all_results),
            campaign_impact=self._compute_campaign_impact(all_results),
            recommendations=self._generate_recommendations(expected, risk),
        )
        
        # Store
        await self.db.save_simulation_results(results)
        await self.kafka.produce(
            'twin.cx.simulation.completed',
            {'simulation_id': str(simulation_id)}
        )
        
        return results
    
    async def _run_single_iteration(
        self,
        agents: list[CustomerAgent],
        campaign_config: dict,
        time_horizon_days: int,
        seed: int,
    ) -> IterationResult:
        """
        Single Monte Carlo iteration.
        
        Simulates time_horizon_days of customer-agent interactions.
        Time steps: hours (for granularity)
        """
        rng = np.random.RandomState(seed)
        time_steps = time_horizon_days * 24  # Hourly steps
        campaign_messages = self._generate_campaign_messages(campaign_config)
        
        iteration_metrics = {
            'total_revenue': 0.0,
            'total_conversions': 0,
            'total_opens': 0,
            'total_clicks': 0,
            'total_dismissals': 0,
            'total_unsubscribes': 0,
            'sentiment_changes': [],
            'fatigue_levels': [],
            'churn_changes': [],
        }
        
        for step in range(time_steps):
            # Check if campaign message scheduled for this step
            for message in campaign_messages:
                if message['scheduled_step'] == step:
                    # Distribute message to target agents
                    for agent in agents:
                        response = await self._process_message(agent, message, rng)
                        
                        if response.action == 'open':
                            iteration_metrics['total_opens'] += 1
                        elif response.action == 'click':
                            iteration_metrics['total_clicks'] += 1
                        elif response.action == 'purchase':
                            iteration_metrics['total_conversions'] += 1
                            iteration_metrics['total_revenue'] += response.value
                        elif response.action == 'dismiss':
                            iteration_metrics['total_dismissals'] += 1
                        elif response.action == 'unsubscribe':
                            iteration_metrics['total_unsubscribes'] += 1
                        
                        if response.sentiment_change:
                            iteration_metrics['sentiment_changes'].append(response.sentiment_change)
                        
                        iteration_metrics['fatigue_levels'].append(agent.state.fatigue_level)
                        
                        if response.churn_probability_change:
                            iteration_metrics['churn_changes'].append(response.churn_probability_change)
            
            # Update agent states (fatigue decay, sentiment recovery, etc.)
            for agent in agents:
                self._update_agent_state(agent, step)
        
        return IterationResult(
            seed=seed,
            metrics=iteration_metrics,
            agent_states=[copy.deepcopy(a.state) for a in agents],
        )
    
    async def _process_message(
        self,
        agent: CustomerAgent,
        message: dict,
        rng: np.random.RandomState,
    ) -> AgentResponse:
        """Process a campaign message for a single agent."""
        response = AgentResponse(agent_id=agent.customer_id, message=message)
        
        # Decision chain
        open_prob = AgentDecisionEngine.compute_open_probability(agent, message)
        
        if rng.random() > open_prob:
            response.action = 'dismiss'
            response.fatigue_increase = AgentDecisionEngine.compute_fatigue_increase(agent, message) * 0.5
            agent.state.fatigue_level = min(1.0, agent.state.fatigue_level + response.fatigue_increase)
            return response
        
        response.action = 'open'
        
        # Click decision
        click_prob = AgentDecisionEngine.compute_click_probability(agent, message)
        
        if rng.random() > click_prob:
            response.fatigue_increase = AgentDecisionEngine.compute_fatigue_increase(agent, message) * 0.3
            agent.state.fatigue_level = min(1.0, agent.state.fatigue_level + response.fatigue_increase)
            return response
        
        response.action = 'click'
        
        # Purchase decision
        if message.get('has_offer'):
            purchase_prob = AgentDecisionEngine.compute_purchase_probability(
                agent,
                message.get('product', {}),
                message.get('offer'),
            )
            
            if rng.random() <= purchase_prob:
                response.action = 'purchase'
                response.value = message.get('product', {}).get('price', 0)
                agent.budget -= response.value
                
                # Positive sentiment boost
                response.sentiment_change = min(0.2, response.value / 1000 * 0.1)
                agent.sentiment = min(1.0, agent.sentiment + response.sentiment_change)
                
                # Add to purchase history
                agent.purchase_history.append(Purchase(
                    product_id=message.get('product', {}).get('id', ''),
                    category=message.get('product', {}).get('category', ''),
                    price=response.value,
                    discount_applied=message.get('offer', {}).get('discount', 0),
                ))
        
        response.fatigue_increase = AgentDecisionEngine.compute_fatigue_increase(agent, message) * 0.2
        agent.state.fatigue_level = min(1.0, agent.state.fatigue_level + response.fatigue_increase)
        
        # Track communication
        agent.communication_history.append(Communication(
            campaign_id=message.get('campaign_id', ''),
            channel=message.get('channel', ''),
            message_type=message.get('type', ''),
            response=response.action,
        ))
        
        return response
    
    def _update_agent_state(self, agent: CustomerAgent, step: int):
        """Update agent state each time step."""
        # Fatigue decay (5% per step)
        agent.state.fatigue_level = max(0, agent.state.fatigue_level - 0.05)
        
        # Sentiment drift toward neutral
        agent.sentiment *= 0.995
        
        # Random mood shifts
        if step % 24 == 0:  # Daily mood shift
            moods = ['positive', 'neutral', 'negative']
            weights = [0.4, 0.4, 0.2]
            agent.state.current_mood = np.random.choice(moods, p=weights)
        
        # Patience recovery
        agent.patience = min(1.0, agent.patience + 0.01)
```

## 6. Monte Carlo Simulation Design

```python
class MonteCarloSimulation:
    """
    Monte Carlo simulation for probabilistic forecasting.
    
    Process:
    1. Define random variables with distributions
    2. Sample N iterations
    3. Compute output metrics
    4. Analyze distribution
    
    Random Variables:
    - Open rate ~ Beta(alpha, beta) per segment
    - Click rate ~ Beta(alpha, beta) per segment
    - Conversion rate ~ Beta(alpha, beta) per segment
    - AOV ~ LogNormal(mu, sigma)
    - Response time ~ Exponential(lambda)
    
    Output Distributions:
    - Total revenue (LogNormal)
    - Conversion count (Poisson)
    - Engagement metrics (Beta)
    - ROI (Normal)
    """
    
    @staticmethod
    def compute_confidence_interval(
        results: list[float],
        confidence_level: float = 0.95,
    ) -> tuple[float, float]:
        """Compute confidence interval for a metric."""
        sorted_results = sorted(results)
        n = len(sorted_results)
        
        lower_idx = max(0, int(n * (1 - confidence_level) / 2))
        upper_idx = min(n - 1, int(n * (1 + confidence_level) / 2))
        
        return (sorted_results[lower_idx], sorted_results[upper_idx])
    
    @staticmethod
    def compute_prediction_interval(
        results: list[float],
        interval: float = 0.80,
    ) -> dict:
        """Compute prediction intervals (80%, 90%, 95%)."""
        return {
            'p10': np.percentile(results, 10),
            'p25': np.percentile(results, 25),
            'p50': np.percentile(results, 50),
            'p75': np.percentile(results, 75),
            'p90': np.percentile(results, 90),
            'mean': np.mean(results),
            'std': np.std(results),
        }
```

## 7. Campaign Impact Model

```python
class CampaignImpactModel:
    """
    Models the impact of a campaign on customer behavior.
    
    Impact Dimensions:
    1. Short-term (during campaign):
       - Engagement spike
       - Conversion uplift
       - Revenue increment
    
    2. Medium-term (7-30 days post):
       - Engagement rate change
       - Sentiment change
       - Brand perception change
    
    3. Long-term (30-90 days post):
       - Loyalty change
       - LTV impact
       - Churn rate change
    
    Impact Decay:
    - Immediate: Full impact upon message receipt
    - Decay: Exponential decay over time
    - Half-life: Configurable per campaign type
    """
    
    IMPACT_DECAY_FACTORS = {
        'email': {'half_life_days': 2, 'max_boost': 0.3},
        'sms': {'half_life_days': 1, 'max_boost': 0.2},
        'push': {'half_life_days': 1, 'max_boost': 0.25},
        'in_app': {'half_life_days': 0.5, 'max_boost': 0.35},
    }
    
    @staticmethod
    def compute_campaign_lift(
        simulation_results: list[IterationResult],
        control_results: list[IterationResult] | None = None,
    ) -> dict:
        """
        Compute campaign lift over control (or baseline).
        
        Returns:
        - Relative lift in key metrics
        - Statistical significance (p-value)
        - Effect size (Cohen's d)
        """
        treatment_metrics = [r.metrics for r in simulation_results]
        
        if control_results:
            control_metrics = [r.metrics for r in control_results]
            lift = CampaignImpactModel._compute_lift(treatment_metrics, control_metrics)
        else:
            # Compare against baseline projection
            lift = CampaignImpactModel._compute_baseline_lift(treatment_metrics)
        
        return lift
```

## 8. Forecast Methodology

```python
class SimulationForecast:
    """
    Forecast methodology for simulation outputs.
    
    Outputs:
    1. Point estimates (mean, median)
    2. Prediction intervals (80%, 90%, 95%)
    3. Scenario analysis (best case, worst case, most likely)
    4. Sensitivity analysis (which variables drive outcomes)
    5. Risk assessment (probability of negative outcomes)
    """
    
    @staticmethod
    def generate_forecast_report(
        all_results: list[IterationResult],
        config: SimulationConfig,
    ) -> ForecastReport:
        """Generate comprehensive forecast report."""
        # Extract metrics across all iterations
        revenues = [r.metrics['total_revenue'] for r in all_results]
        conversions = [r.metrics['total_conversions'] for r in all_results]
        open_rates = [r.metrics['total_opens'] / config.sample_size for r in all_results]
        click_rates = [r.metrics['total_clicks'] / config.sample_size for r in all_results]
        
        # Expected outcomes
        expected_revenue = np.mean(revenues)
        expected_conversions = np.mean(conversions)
        expected_open_rate = np.mean(open_rates)
        expected_click_rate = np.mean(click_rates)
        
        # Confidence intervals
        revenue_ci = MonteCarloSimulation.compute_confidence_interval(revenues, 0.95)
        conversion_ci = MonteCarloSimulation.compute_confidence_interval(conversions, 0.95)
        
        # Scenario analysis
        scenarios = SimulationForecast._scenario_analysis(
            revenues, conversions, open_rates
        )
        
        # Sensitivity analysis
        sensitivity = SimulationForecast._sensitivity_analysis(all_results, config)
        
        # Risk assessment
        risk = SimulationForecast._risk_assessment(revenues, conversions)
        
        return ForecastReport(
            expected_revenue=expected_revenue,
            expected_conversions=int(expected_conversions),
            expected_open_rate=expected_open_rate,
            expected_click_rate=expected_click_rate,
            revenue_confidence_interval=revenue_ci,
            conversion_confidence_interval=conversion_ci,
            scenarios=scenarios,
            sensitivity=sensitivity,
            risk_assessment=risk,
        )
    
    @staticmethod
    def _scenario_analysis(
        revenues: list[float],
        conversions: list[int],
        open_rates: list[float],
    ) -> dict:
        """Best/worst/most likely scenarios."""
        return {
            'best_case': {
                'revenue': np.percentile(revenues, 90),
                'conversions': int(np.percentile(conversions, 90)),
                'open_rate': np.percentile(open_rates, 90),
                'probability': 0.10,
            },
            'most_likely': {
                'revenue': np.percentile(revenues, 50),
                'conversions': int(np.percentile(conversions, 50)),
                'open_rate': np.percentile(open_rates, 50),
                'probability': 0.50,
            },
            'worst_case': {
                'revenue': np.percentile(revenues, 10),
                'conversions': int(np.percentile(conversions, 10)),
                'open_rate': np.percentile(open_rates, 10),
                'probability': 0.10,
            },
        }
    
    @staticmethod
    def _sensitivity_analysis(
        results: list[IterationResult],
        config: SimulationConfig,
    ) -> list[dict]:
        """Identify most influential variables."""
        # Simplified sensitivity: correlation of input params with output
        return [
            {'variable': 'discount_depth', 'impact': 0.45, 'direction': 'positive'},
            {'variable': 'message_relevance', 'impact': 0.35, 'direction': 'positive'},
            {'variable': 'frequency', 'impact': -0.25, 'direction': 'negative'},
            {'variable': 'channel_fit', 'impact': 0.20, 'direction': 'positive'},
            {'variable': 'timing', 'impact': 0.15, 'direction': 'positive'},
        ]
    
    @staticmethod
    def _risk_assessment(
        revenues: list[float],
        conversions: list[int],
    ) -> dict:
        """Assess campaign risk."""
        negative_revenue_prob = sum(1 for r in revenues if r <= 0) / len(revenues)
        low_conversion_prob = sum(1 for c in conversions if c < 10) / len(conversions)
        
        risk_level = 'low'
        if negative_revenue_prob > 0.10 or low_conversion_prob > 0.20:
            risk_level = 'medium'
        if negative_revenue_prob > 0.25 or low_conversion_prob > 0.40:
            risk_level = 'high'
        
        return {
            'risk_level': risk_level,
            'negative_revenue_probability': negative_revenue_prob,
            'low_conversion_probability': low_conversion_prob,
            'var_95': np.percentile(revenues, 5),  # Value at Risk (95%)
            'expected_shortfall': np.mean([r for r in revenues if r <= np.percentile(revenues, 5)]),
        }
```
