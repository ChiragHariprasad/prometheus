-- Migration: Add missing indexes identified by codebase audit (2026-06-21)
-- Apply: psql -U prometheus -d prometheus -f 002_missing_indexes.sql

BEGIN;

-- 1. customer_events.campaign_id — used by process_event campaign conversion lookup
CREATE INDEX IF NOT EXISTS idx_events_campaign ON customer_events(organization_id, campaign_id)
    WHERE campaign_id IS NOT NULL;

-- 2. customer_twins.customer_id — fast twin lookup by customer (covered by unique constraint, but adding org-scoped)
CREATE INDEX IF NOT EXISTS idx_customer_twins_customer_org ON customer_twins(organization_id, customer_id);

-- 3. customer_predictions.created_at — for listing recent predictions
CREATE INDEX IF NOT EXISTS idx_predictions_created ON customer_predictions(organization_id, created_at DESC);

-- 4. customer_segments.created_by — FK lookup
CREATE INDEX IF NOT EXISTS idx_segments_created_by ON customer_segments(created_by)
    WHERE created_by IS NOT NULL;

-- 5. campaign_targets(customer_id, campaign_id) — for merge and lookup
CREATE INDEX IF NOT EXISTS idx_campaign_targets_customer_campaign ON campaign_targets(organization_id, customer_id, campaign_id);

-- 6. notifications(customer_id, created_at) — for notification listing by customer
CREATE INDEX IF NOT EXISTS idx_notifications_customer_created ON notifications(organization_id, customer_id, created_at DESC);

-- 7. recommendations(customer_id, is_applied) — for personalized recommendations query
CREATE INDEX IF NOT EXISTS idx_recommendations_applied_customer ON recommendations(organization_id, customer_id, is_applied)
    WHERE is_applied = false;

-- 8. simulations(organization_id, created_at) — for simulation listing
CREATE INDEX IF NOT EXISTS idx_simulations_created ON simulations(organization_id, created_at DESC);

-- 9. customer_events.idempotency_key — for deduplication (partial, only when key is set)
CREATE INDEX IF NOT EXISTS ix_customer_events_idempotency_key ON customer_events(organization_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

COMMIT;
