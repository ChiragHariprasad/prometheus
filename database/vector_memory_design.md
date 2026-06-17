# Vector Memory System - Qdrant Design

## 1. Collections

```python
COLLECTIONS = {
    "customer_embeddings": {
        "vectors": {
            "size": 1024,  # bge-large-en-v1.5 output dimension
            "distance": "Cosine",
        },
        "shard_number": 6,
        "replication_factor": 2,
        "write_consistency_factor": 1,
        "on_disk_payload": True,
        "optimizers_config": {
            "default_segment_number": 16,
            "indexing_threshold": 10000,
        },
        "hnsw_config": {
            "m": 16,
            "ef_construct": 100,
            "full_scan_threshold": 10000,
        },
        "quantization_config": {
            "scalar": {
                "type": "int8",
                "quantile": 0.99,
                "always_ram": True,
            }
        }
    },
    "customer_interests": {
        "vectors": {
            "size": 1024,
            "distance": "Cosine",
        },
        "shard_number": 6,
        "replication_factor": 2,
        "on_disk_payload": True,
    },
    "product_embeddings": {
        "vectors": {
            "size": 1024,
            "distance": "Cosine",
        },
        "shard_number": 4,
        "replication_factor": 2,
        "on_disk_payload": True,
    },
    "campaign_embeddings": {
        "vectors": {
            "size": 1024,
            "distance": "Cosine",
        },
        "shard_number": 4,
        "replication_factor": 2,
        "on_disk_payload": True,
    },
    "semantic_memory": {
        "vectors": {
            "size": 1024,
            "distance": "Cosine",
        },
        "shard_number": 4,
        "replication_factor": 2,
        "on_disk_payload": True,
    },
}
```

## 2. Payload Schema

```python
class CustomerEmbeddingPayload(BaseModel):
    organization_id: str
    customer_id: str
    external_id: str | None
    email: str | None
    first_name: str | None
    last_name: str | None
    
    # Demographic
    age_group: str | None
    gender: str | None
    location: str | None
    timezone: str | None
    locale: str | None
    
    # Behavioral
    lifecycle_stage: str
    rfm_segment: str
    engagement_tier: str  # high, medium, low
    loyalty_tier: str     # gold, silver, bronze
    
    # Scores
    engagement_score: float
    loyalty_score: float
    lifetime_value: float
    
    # Risk
    churn_probability: float
    churn_risk_level: str
    
    # Interests (for filtering)
    top_categories: list[str]
    top_brands: list[str]
    
    # Metadata
    embedding_version: int
    last_event_at: int  # unix timestamp
    updated_at: int


class InterestEmbeddingPayload(BaseModel):
    organization_id: str
    customer_id: str
    category: str
    subcategory: str | None
    interest_level: float
    affinity_score: float
    interaction_count: int
    source: str
    is_active: bool
    updated_at: int


class ProductEmbeddingPayload(BaseModel):
    organization_id: str
    product_id: str
    name: str
    description: str
    category: str
    subcategory: str | None
    brand: str | None
    price: float
    currency: str
    tags: list[str]
    attributes: dict
    is_active: bool
    created_at: int


class SemanticMemoryPayload(BaseModel):
    organization_id: str
    memory_id: str
    customer_id: str | None
    memory_type: str  # conversation, preference, feedback, context
    content: str
    summary: str
    sentiment: float
    importance: float  # 0.0 - 1.0
    tags: list[str]
    source: str
    expires_at: int | None
    created_at: int
```

## 3. Embedding Pipeline

```python
class EmbeddingPipeline:
    """
    Pipeline stages:
    1. Data collection -> 2. Text construction -> 3. Embedding generation -> 4. Storage
    
    Embedding Model: BAAI/bge-large-en-v1.5
    - 1024 dimensions
    - Supports dense retrieval
    - Optimized for cosine similarity
    - Max tokens: 512
    - Instruction: "Represent this customer profile for similarity search:"
    """
    
    @staticmethod
    def construct_customer_text(customer: dict, profile: dict, twin: dict) -> str:
        """Build text representation for embedding"""
        sections = []
        
        # Demographics
        sections.append(f"Customer is a {customer.get('gender', 'unknown')} aged {customer.get('age_group', 'unknown')} from {customer.get('location', 'unknown')}.")
        
        # Behavior summary
        bp = twin.get('behavior_profile', {})
        sections.append(f"Engagement: {bp.get('sessions_per_week', 0):.1f} sessions/week, {bp.get('avg_session_duration', 0):.0f}s average session.")
        sections.append(f"Purchase behavior: {bp.get('purchase_frequency', 0):.2f} purchases/month, {bp.get('avg_order_value', 0):.2f} AOV.")
        
        # Interests
        interests = twin.get('interest_graph', {}).get('nodes', {})
        top_interests = sorted(interests.items(), key=lambda x: x[1].get('interest_level', 0), reverse=True)[:5]
        if top_interests:
            sections.append(f"Interests: {', '.join(f'{cat}({data.get(\"interest_level\", 0):.0%})' for cat, data in top_interests)}.")
        
        # Lifecycle
        sections.append(f"Lifecycle stage: {bp.get('lifecycle_stage', 'unknown')}.")
        sections.append(f"RFM segment: {bp.get('rfm_segment', 'unknown')}.")
        
        # Risk
        risk = twin.get('risk_indicators', {})
        sections.append(f"Churn risk: {risk.get('churn_risk_level', 'unknown')}.")
        
        # Scores
        sections.append(f"Engagement: {twin.get('engagement_score', 0):.2f}, Loyalty: {twin.get('loyalty_score', 0):.2f}, LTV: {twin.get('lifetime_value', 0):.2f}.")
        
        text = " ".join(sections)
        # Truncate to model max tokens (conservative char limit)
        return text[:2000]
    
    @staticmethod
    async def generate_embedding(text: str, model_client) -> list[float]:
        """Generate embedding using bge-large-en-v1.5"""
        instruction = "Represent this customer profile for similarity search:"
        input_text = f"{instruction} {text}"
        
        embedding = await model_client.embed(
            model="BAAI/bge-large-en-v1.5",
            input=[input_text],
            encoding_format="float",
        )
        return embedding[0]
```

## 4. Memory Update Pipeline

```python
class MemoryUpdatePipeline:
    """
    Real-time memory updates on event arrival:
    
    Event -> Extract relevant info -> Generate embedding -> Store with payload
    
    Update triggers:
    - New event (any type): Update customer embedding if event count > threshold
    - New interest detected: Update interest embedding
    - Profile change: Update customer embedding immediately
    - Twin rebuild: Full embedding regeneration
    - Session end: Update behavior context in semantic memory
    """
    
    BATCH_SIZE = 100
    UPDATE_COOLDOWN_SECONDS = 300  # Min 5 min between updates per customer
    
    async def process_event(self, event: dict):
        customer_id = event['customer_id']
        
        # Check cooldown
        last_update = await self.redis.get(f"emb:cooldown:{customer_id}")
        if last_update:
            return
        
        # Determine update type
        event_type = event['event_type']
        
        if event_type in ('purchase', 'page_view', 'session'):
            # Incremental update - just update scores
            await self.update_customer_scores(customer_id, event)
            
            # Batch full updates
            if await self.should_full_update(customer_id):
                task = {
                    'customer_id': customer_id,
                    'org_id': event['organization_id'],
                    'type': 'full_embedding_update'
                }
                await self.kafka.produce('twin.cx.embeddings.update', task)
        
        elif event_type in ('support_ticket', 'social_interaction'):
            # Add to semantic memory
            await self.add_semantic_memory(customer_id, event)
    
    async def full_embedding_update(self, customer_id: UUID, org_id: UUID):
        """Full embedding regeneration"""
        # Get customer data
        customer = await self.db.get_customer(org_id, customer_id)
        profile = await self.db.get_customer_profile(org_id, customer_id)
        twin = await self.db.get_customer_twin(org_id, customer_id)
        
        # Construct text
        text = EmbeddingPipeline.construct_customer_text(customer, profile, twin)
        
        # Generate embedding
        embedding = await EmbeddingPipeline.generate_embedding(text, self.model_client)
        
        # Prepare payload
        payload = CustomerEmbeddingPayload(
            organization_id=str(org_id),
            customer_id=str(customer_id),
            external_id=customer.get('external_id'),
            email=customer.get('email'),
            first_name=customer.get('first_name'),
            last_name=customer.get('last_name'),
            age_group=profile.get('age_group'),
            engagement_score=twin['engagement_score'],
            loyalty_score=twin['loyalty_score'],
            lifetime_value=twin['lifetime_value'],
            churn_probability=twin.get('risk_indicators', {}).get('churn_probability', 0),
            churn_risk_level=twin.get('risk_indicators', {}).get('churn_risk_level', 'low'),
            top_categories=list(twin.get('interest_graph', {}).get('nodes', {}).keys())[:10],
            lifecycle_stage=twin.get('behavior_profile', {}).get('lifecycle_stage', 'unknown'),
            rfm_segment=twin.get('behavior_profile', {}).get('rfm_segment', 'unknown'),
            engagement_tier=self.classify_tier(twin['engagement_score']),
            loyalty_tier=self.classify_tier(twin['loyalty_score']),
            embedding_version=twin['version'],
            last_event_at=int(twin.get('last_event_at', datetime.utcnow()).timestamp()),
            updated_at=int(datetime.utcnow().timestamp()),
        )
        
        # Store in Qdrant
        point = PointStruct(
            id=self.generate_uuid(),
            vector=embedding,
            payload=payload.dict(),
        )
        
        await self.qdrant.upsert(
            collection_name="customer_embeddings",
            points=[point],
        )
        
        # Set cooldown
        await self.redis.setex(
            f"emb:cooldown:{customer_id}",
            self.UPDATE_COOLDOWN_SECONDS,
            "1"
        )
```

## 5. Retrieval Architecture

```python
class VectorRetrievalService:
    """
    Hybrid search combining vector similarity + metadata filtering + keyword search.
    
    Search types:
    1. Similar customers (lookalike): Find customers similar to a seed customer
    2. Interest-based: Find customers with specific interests
    3. Behavioral: Find customers matching behavior patterns
    4. Semantic: Natural language search for customer segments
    5. Hybrid: Combine all approaches
    """
    
    async def find_similar_customers(
        self,
        org_id: UUID,
        customer_id: UUID,
        limit: int = 20,
        filters: dict | None = None,
    ) -> list[CustomerEmbeddingPayload]:
        """Lookalike audience discovery"""
        # Get seed customer embedding
        seed = await self.qdrant.search(
            collection_name="customer_embeddings",
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="organization_id",
                        match=MatchValue(value=str(org_id)),
                    ),
                    FieldCondition(
                        key="customer_id",
                        match=MatchValue(value=str(customer_id)),
                    ),
                ]
            ),
            limit=1,
        )
        
        if not seed:
            return []
        
        # Build search filter
        search_filter = self._build_filter(org_id, filters)
        
        # Search by vector similarity
        results = await self.qdrant.search(
            collection_name="customer_embeddings",
            query_vector=seed[0].vector,
            query_filter=search_filter,
            limit=limit + 1,  # +1 for seed
        )
        
        # Exclude seed customer
        return [
            r.payload for r in results
            if r.payload.get('customer_id') != str(customer_id)
        ][:limit]
    
    async def semantic_search(
        self,
        org_id: UUID,
        query: str,
        limit: int = 20,
        filters: dict | None = None,
    ) -> list[CustomerEmbeddingPayload]:
        """Natural language search for customers"""
        # Generate query embedding
        instruction = "Represent this customer search query:"
        query_embedding = await EmbeddingPipeline.generate_embedding(
            f"{instruction} {query}",
            self.model_client,
        )
        
        # Build search filter
        search_filter = self._build_filter(org_id, filters)
        
        # Search
        results = await self.qdrant.search(
            collection_name="customer_embeddings",
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
        )
        
        return [r.payload for r in results]
    
    async def hybrid_search(
        self,
        org_id: UUID,
        query: str | None = None,
        customer_id: UUID | None = None,
        filters: dict | None = None,
        limit: int = 20,
        alpha: float = 0.7,  # Weight between vector (0.7) and keyword (0.3)
    ) -> list[CustomerEmbeddingPayload]:
        """
        Hybrid search combining:
        - Dense retrieval (vector similarity)
        - Sparse retrieval (keyword/BM25)
        - Metadata filtering
        
        alpha: 0.0 = pure keyword, 1.0 = pure vector
        """
        search_filter = self._build_filter(org_id, filters)
        
        if query:
            # Generate embedding
            query_embedding = await EmbeddingPipeline.generate_embedding(
                f"Represent this customer search query: {query}",
                self.model_client,
            )
            
            # Use Qdrant's built-in hybrid search
            results = await self.qdrant.search(
                collection_name="customer_embeddings",
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                with_payload=True,
                score_threshold=0.5,
            )
        else:
            results = await self.qdrant.scroll(
                collection_name="customer_embeddings",
                filter=search_filter,
                limit=limit,
            )
        
        return [r.payload for r in results]
    
    def _build_filter(self, org_id: UUID, filters: dict | None = None) -> Filter:
        """Build Qdrant filter from query parameters"""
        must_conditions = [
            FieldCondition(
                key="organization_id",
                match=MatchValue(value=str(org_id)),
            )
        ]
        
        if filters:
            for key, value in filters.items():
                if isinstance(value, dict):
                    if 'gte' in value or 'lte' in value:
                        must_conditions.append(
                            RangeCondition(
                                key=key,
                                **value,
                            )
                        )
                    elif 'in' in value:
                        must_conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchAny(any=value['in']),
                            )
                        )
                else:
                    must_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
        
        return Filter(must=must_conditions)
```

## 6. Semantic Memory Design

```python
class SemanticMemoryService:
    """
    Episodic and semantic memory for customer interactions.
    
    Memory types:
    - Episodic: Specific interactions, events, conversations
    - Semantic: General knowledge about customer preferences
    - Procedural: How customer typically behaves
    - Reflective: Customer feedback and sentiment
    """
    
    MEMORY_TYPES = {
        'conversation': {'ttl_days': 90, 'importance_decay': 0.1},
        'preference': {'ttl_days': 365, 'importance_decay': 0.01},
        'feedback': {'ttl_days': 365, 'importance_decay': 0.05},
        'context': {'ttl_days': 30, 'importance_decay': 0.2},
        'intent': {'ttl_days': 60, 'importance_decay': 0.15},
    }
    
    async def store_memory(
        self,
        org_id: UUID,
        customer_id: UUID | None,
        memory_type: str,
        content: str,
        summary: str | None = None,
        sentiment: float = 0.0,
        importance: float = 0.5,
        tags: list[str] | None = None,
        source: str = "system",
    ):
        """Store a memory in semantic memory collection"""
        # Generate embedding for the memory content
        text = f"[{memory_type}] {content}"
        embedding = await EmbeddingPipeline.generate_embedding(text, self.model_client)
        
        # Calculate expiry
        config = self.MEMORY_TYPES.get(memory_type, {})
        ttl_days = config.get('ttl_days', 90)
        expires_at = int((datetime.utcnow() + timedelta(days=ttl_days)).timestamp())
        
        point = PointStruct(
            id=uuid4().hex,
            vector=embedding,
            payload=SemanticMemoryPayload(
                organization_id=str(org_id),
                memory_id=uuid4().hex,
                customer_id=str(customer_id) if customer_id else None,
                memory_type=memory_type,
                content=content,
                summary=summary or content[:200],
                sentiment=sentiment,
                importance=importance,
                tags=tags or [],
                source=source,
                expires_at=expires_at,
                created_at=int(datetime.utcnow().timestamp()),
            ).dict(),
        )
        
        await self.qdrant.upsert(
            collection_name="semantic_memory",
            points=[point],
        )
    
    async def recall_memories(
        self,
        org_id: UUID,
        query: str,
        customer_id: UUID | None = None,
        memory_type: str | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> list[SemanticMemoryPayload]:
        """Retrieve relevant memories"""
        # Generate query embedding
        query_embedding = await EmbeddingPipeline.generate_embedding(query, self.model_client)
        
        # Build filter
        must_conditions = [
            FieldCondition(
                key="organization_id",
                match=MatchValue(value=str(org_id)),
            ),
            RangeCondition(key="importance", gte=min_importance),
        ]
        
        if customer_id:
            must_conditions.append(
                FieldCondition(
                    key="customer_id",
                    match=MatchValue(value=str(customer_id)),
                )
            )
        
        if memory_type:
            must_conditions.append(
                FieldCondition(
                    key="memory_type",
                    match=MatchValue(value=memory_type),
                )
            )
        
        # Exclude expired
        must_conditions.append(
            RangeCondition(
                key="expires_at",
                gte=int(datetime.utcnow().timestamp()),
            )
        )
        
        results = await self.qdrant.search(
            collection_name="semantic_memory",
            query_vector=query_embedding,
            query_filter=Filter(must=must_conditions),
            limit=limit,
        )
        
        return [SemanticMemoryPayload(**r.payload) for r in results]
    
    async def consolidate_memories(self, org_id: UUID, customer_id: UUID):
        """
        Consolidate short-term memories into long-term knowledge.
        - Summarize recent conversations
        - Update preference memory based on patterns
        - Prune low-importance expired memories
        """
        # Get recent memories
        recent = await self.qdrant.scroll(
            collection_name="semantic_memory",
            filter=Filter(
                must=[
                    FieldCondition(key="organization_id", match=MatchValue(value=str(org_id))),
                    FieldCondition(key="customer_id", match=MatchValue(value=str(customer_id))),
                    FieldCondition(key="memory_type", match=MatchValue(value="conversation")),
                ]
            ),
            limit=100,
        )
        
        if len(recent) > 10:
            # Summarize and create consolidated memory
            texts = [r.payload['content'] for r in recent]
            summary = await self.summarize_texts(texts, self.llm_client)
            
            await self.store_memory(
                org_id=org_id,
                customer_id=customer_id,
                memory_type='preference',
                content=summary,
                summary=summary[:200],
                importance=0.8,
                tags=['consolidated', 'conversation_summary'],
                source='memory_consolidation',
            )
            
            # Delete old conversation memories (keep last 10)
            old_memories = sorted(recent, key=lambda x: x.payload['created_at'])[:-10]
            for mem in old_memories:
                await self.qdrant.delete(
                    collection_name="semantic_memory",
                    points_selector=PointIdsList(points=[mem.id]),
                )
```
