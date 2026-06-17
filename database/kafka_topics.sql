-- PROMETHEUS Kafka Topic Definitions
-- Schema Registry: Avro + JSON Schema compatibility

-- ============================================================
-- TOPIC: twin.cx.events.raw
-- Purpose: Raw event ingestion from all sources
-- Partitions: 12 (scale with customer base)
-- Replication: 3
-- Retention: 30 days
-- Compact: false
-- ============================================================
-- Key: customer_id (UUID)
-- Value: RawEvent (Avro)
-- Schema:
{
  "type": "record",
  "name": "RawEvent",
  "namespace": "com.prometheus.event",
  "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "organization_id", "type": "string"},
    {"name": "customer_id", "type": "string"},
    {"name": "session_id", "type": ["null", "string"], "default": null},
    {"name": "event_type", "type": "string"},
    {"name": "event_name", "type": "string"},
    {"name": "event_properties", "type": {"type": "map", "values": "string"}},
    {"name": "context", "type": {"type": "map", "values": "string"}},
    {"name": "channel", "type": ["null", "string"], "default": null},
    {"name": "source", "type": ["null", "string"], "default": null},
    {"name": "device_type", "type": ["null", "string"], "default": null},
    {"name": "device_os", "type": ["null", "string"], "default": null},
    {"name": "browser", "type": ["null", "string"], "default": null},
    {"name": "ip_address", "type": ["null", "string"], "default": null},
    {"name": "user_agent", "type": ["null", "string"], "default": null},
    {"name": "referrer", "type": ["null", "string"], "default": null},
    {"name": "url", "type": ["null", "string"], "default": null},
    {"name": "geolocation", "type": ["null", "string"], "default": null},
    {"name": "campaign_id", "type": ["null", "string"], "default": null},
    {"name": "value", "type": ["null", "double"], "default": null},
    {"name": "currency", "type": ["null", "string"], "default": null},
    {"name": "event_timestamp", "type": "long"},
    {"name": "ingested_at", "type": "long"}
  ]
}

-- ============================================================
-- TOPIC: twin.cx.events.pageview
-- Key: customer_id
-- Value: PageViewEvent
-- Schema:
-- {
--   "name": "PageViewEvent",
--   "fields": [
--     {"name": "url", "type": "string"},
--     {"name": "page_title", "type": "string"},
--     {"name": "page_category", "type": ["null", "string"]},
--     {"name": "referrer", "type": ["null", "string"]},
--     {"name": "time_on_page_ms", "type": "int"},
--     {"name": "scroll_depth_pct", "type": "int"},
--     {"name": "interaction_count", "type": "int"}
--   ]
-- }

-- ============================================================
-- TOPIC: twin.cx.events.purchase
-- Key: customer_id
-- Value: PurchaseEvent
-- Schema:
-- {
--   "name": "PurchaseEvent",
--   "fields": [
--     {"name": "order_id", "type": "string"},
--     {"name": "product_id", "type": "string"},
--     {"name": "product_category", "type": "string"},
--     {"name": "product_name", "type": "string"},
--     {"name": "quantity", "type": "int"},
--     {"name": "unit_price", "type": "double"},
--     {"name": "total_amount", "type": "double"},
--     {"name": "currency", "type": "string"},
--     {"name": "discount_applied", "type": "double"},
--     {"name": "payment_method", "type": "string"},
--     {"name": "is_first_purchase", "type": "boolean"},
--     {"name": "is_recurring", "type": "boolean"}
--   ]
-- }

-- ============================================================
-- TOPIC: twin.cx.events.email
-- Key: customer_id
-- Value: EmailEvent (covers open + click)
-- Schema:
-- {
--   "name": "EmailEvent",
--   "fields": [
--     {"name": "email_id", "type": "string"},
--     {"name": "campaign_id", "type": ["null", "string"]},
--     {"name": "event_type", "type": {"enum": "email_event_type", "symbols": ["sent", "delivered", "opened", "clicked", "bounced", "unsubscribed", "spam"]}},
--     {"name": "link_url", "type": ["null", "string"]},
--     {"name": "link_text", "type": ["null", "string"]},
--     {"name": "subject_line", "type": ["null", "string"]},
--     {"name": "email_variant", "type": ["null", "string"]}
--   ]
-- }

-- ============================================================
-- TOPIC: twin.cx.events.session
-- Key: customer_id
-- Value: SessionEvent
-- Schema:
-- {
--   "name": "SessionEvent",
--   "fields": [
--     {"name": "session_id", "type": "string"},
--     {"name": "session_start", "type": "long"},
--     {"name": "session_end", "type": ["null", "long"]},
--     {"name": "duration_seconds", "type": "int"},
--     {"name": "page_views", "type": "int"},
--     {"name": "events_count", "type": "int"},
--     {"name": "channel", "type": "string"},
--     {"name": "is_bounce", "type": "boolean"},
--     {"name": "landing_url", "type": "string"},
--     {"name": "exit_url", "type": ["null", "string"]},
--     {"name": "utm_source", "type": ["null", "string"]},
--     {"name": "utm_medium", "type": ["null", "string"]},
--     {"name": "utm_campaign", "type": ["null", "string"]}
--   ]
-- }

-- ============================================================
-- TOPIC: twin.cx.events.support
-- Key: customer_id
-- Value: SupportTicketEvent
-- Schema:
-- {
--   "name": "SupportTicketEvent",
--   "fields": [
--     {"name": "ticket_id", "type": "string"},
--     {"name": "ticket_type", "type": "string"},
--     {"name": "ticket_status", "type": "string"},
--     {"name": "ticket_priority", "type": "string"},
--     {"name": "ticket_category", "type": "string"},
--     {"name": "subject", "type": "string"},
--     {"name": "description_length", "type": "int"},
--     {"name": "resolution_time_minutes", "type": ["null", "int"]},
--     {"name": "customer_satisfaction_score", "type": ["null", "int"]},
--     {"name": "assigned_agent", "type": ["null", "string"]},
--     {"name": "is_escalated", "type": "boolean"},
--     {"name": "is_resolved", "type": "boolean"}
--   ]
-- }

-- ============================================================
-- TOPIC: twin.cx.events.campaign
-- Key: customer_id
-- Value: CampaignResponseEvent
-- Schema:
-- {
--   "name": "CampaignResponseEvent",
--   "fields": [
--     {"name": "campaign_id", "type": "string"},
--     {"name": "campaign_name", "type": "string"},
--     {"name": "campaign_type", "type": "string"},
--     {"name": "channel", "type": "string"},
--     {"name": "response_type", "type": {"enum": "response_type", "symbols": ["received", "opened", "clicked", "converted", "dismissed", "unsubscribed"]}},
--     {"name": "treatment", "type": "string"},
--     {"name": "conversion_value", "type": ["null", "double"]},
--     {"name": "time_to_response_minutes", "type": ["null", "int"]}
--   ]
-- }

-- ============================================================
-- TOPIC: twin.cx.events.social
-- Key: customer_id
-- Value: SocialInteractionEvent
-- Schema:
-- {
--   "name": "SocialInteractionEvent",
--   "fields": [
--     {"name": "platform", "type": "string"},
--     {"name": "interaction_type", "type": {"enum": "social_type", "symbols": ["like", "share", "comment", "follow", "unfollow", "mention", "direct_message"]}},
--     {"name": "content_id", "type": ["null", "string"]},
--     {"name": "content_text", "type": ["null", "string"]},
--     {"name": "content_category", "type": ["null", "string"]},
--     {"name": "influencer_score", "type": ["null", "double"]},
--     {"name": "engagement_rate", "type": ["null", "double"]}
--   ]
-- }

-- ============================================================
-- TOPIC: twin.cx.twin.update
-- Purpose: Digital twin update notifications
-- Partitions: 12
-- Retention: 7 days
-- Compact: true (log compaction for latest state)
-- ============================================================
-- Key: customer_id
-- Value: TwinUpdateEvent
-- Schema:
-- {
--   "name": "TwinUpdateEvent",
--   "fields": [
--     {"name": "customer_id", "type": "string"},
--     {"name": "twin_version", "type": "int"},
--     {"name": "update_type", "type": {"enum": "twin_update_type", "symbols": ["behavior", "interest", "sentiment", "engagement", "loyalty", "ltv", "prediction", "full_rebuild"]}},
--     {"name": "scores", "type": {"type": "map", "values": "double"}},
--     {"name": "changed_attributes", "type": {"type": "array", "items": "string"}},
--     {"name": "triggered_by_event_id", "type": ["null", "string"]},
--     {"name": "computation_time_ms", "type": "int"},
--     {"name": "confidence_score", "type": "double"}
--   ]
-- }

-- ============================================================
-- TOPIC: twin.cx.prediction
-- Purpose: Prediction results for real-time actions
-- Partitions: 6
-- Retention: 7 days
-- ============================================================
-- Key: customer_id
-- Value: PredictionEvent
-- Schema:
-- {
--   "name": "PredictionEvent",
--   "fields": [
--     {"name": "customer_id", "type": "string"},
--     {"name": "prediction_type", "type": "string"},
--     {"name": "prediction_value", "type": "double"},
--     {"name": "prediction_probability", "type": ["null", "double"]},
--     {"name": "prediction_label", "type": ["null", "string"]},
--     {"name": "model_name", "type": "string"},
--     {"name": "model_version", "type": "string"},
--     {"name": "confidence_score", "type": "double"},
--     {"name": "valid_until", "type": ["null", "long"]}
--   ]
-- }

-- ============================================================
-- TOPIC: twin.cx.notification
-- Purpose: Trigger notifications across channels
-- Partitions: 6
-- Retention: 3 days
-- ============================================================
-- Key: customer_id
-- Value: NotificationTrigger
-- Schema: notification_id, customer_id, channel, template_id, data

-- ============================================================
-- TOPIC: twin.cx.simulation
-- Purpose: Simulation job distribution
-- Partitions: 6
-- Retention: 14 days
-- ============================================================
-- Key: simulation_id
-- Value: SimulationJob
-- Schema: simulation_id, run_config, agent_count, seed, iteration

-- ============================================================
-- TOPIC: twin.cx.dead.letter
-- Purpose: Failed event storage for reprocessing
-- Partitions: 3
-- Retention: 90 days
-- ============================================================
-- Key: original_topic + partition + offset
-- Value: DeadLetterMessage
-- Schema:
-- {
--   "name": "DeadLetterMessage",
--   "fields": [
--     {"name": "original_topic", "type": "string"},
--     {"name": "original_partition", "type": "int"},
--     {"name": "original_offset", "type": "long"},
--     {"name": "original_key", "type": "string"},
--     {"name": "original_value", "type": "string"},
--     {"name": "error_type", "type": "string"},
--     {"name": "error_message", "type": "string"},
--     {"name": "error_traceback", "type": "string"},
--     {"name": "retry_count", "type": "int"},
--     {"name": "failed_at", "type": "long"}
--   ]
-- }

-- ============================================================
-- KAFKA CONSUMER GROUPS
-- ============================================================
-- Consumer Group: twin-cx-event-router
--   Topics: twin.cx.events.raw
--   Purpose: Route raw events to typed topics

-- Consumer Group: twin-cx-twin-builder
--   Topics: twin.cx.events.*
--   Purpose: Build and update digital twins

-- Consumer Group: twin-cx-predictor
--   Topics: twin.cx.events.*, twin.cx.twin.update
--   Purpose: Run real-time predictions

-- Consumer Group: twin-cx-simulator
--   Topics: twin.cx.simulation
--   Purpose: Execute simulation runs

-- Consumer Group: twin-cx-notifier
--   Topics: twin.cx.prediction, twin.cx.notification
--   Purpose: Send notifications

-- Consumer Group: twin-cx-dlq-reprocessor
--   Topics: twin.cx.dead.letter
--   Purpose: Reprocess failed messages

-- ============================================================
-- KAFKA CONFIGURATION
-- ============================================================
-- producer:
--   acks: all (guaranteed delivery)
--   compression.type: zstd
--   linger.ms: 10
--   batch.size: 65536
--   enable.idempotence: true
--   max.in.flight.requests.per.connection: 5

-- consumer:
--   auto.offset.reset: earliest
--   enable.auto.commit: false
--   isolation.level: read_committed
--   max.poll.records: 500
--   session.timeout.ms: 30000
--   heartbeat.interval.ms: 3000

-- retry:
--   max.retries: 3
--   retry.backoff.ms: 1000
--   retry.backoff.max.ms: 30000

-- dlq:
--   enabled: true
--   max.retries: 3
--   after: dead.letter.topic
