-- PROMETHEUS PostgreSQL Schema
-- Enterprise-grade schema for 100K+ customers, 10M+ events

-- ============================================================
-- EXTENSIONS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ============================================================
-- ENUMS
-- ============================================================
CREATE TYPE event_type AS ENUM (
    'page_view', 'purchase', 'email_open', 'email_click',
    'session', 'support_ticket', 'campaign_response',
    'social_interaction', 'app_open', 'app_close',
    'search', 'add_to_cart', 'remove_from_cart',
    'wishlist_add', 'wishlist_remove', 'review_submit',
    'referral', 'redemption', 'login', 'logout'
);

CREATE TYPE twin_status AS ENUM ('active', 'stale', 'archived', 'building');
CREATE TYPE simulation_status AS ENUM ('draft', 'running', 'completed', 'failed', 'cancelled');
CREATE TYPE campaign_status AS ENUM ('draft', 'scheduled', 'active', 'paused', 'completed', 'cancelled');
CREATE TYPE notification_channel AS ENUM ('email', 'sms', 'push', 'in_app', 'webhook');
CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed');
CREATE TYPE segment_source AS ENUM ('rule_based', 'ml_cluster', 'lookalike', 'custom', 'imported');
CREATE TYPE prediction_target AS ENUM ('churn', 'ltv', 'conversion', 'engagement', 'sentiment', 'intent', 'next_best_action');
CREATE TYPE permission_resource AS ENUM (
    'customers', 'campaigns', 'simulations', 'analytics',
    'users', 'settings', 'billing', 'integrations',
    'segments', 'predictions', 'twins', 'notifications'
);
CREATE TYPE permission_action AS ENUM ('create', 'read', 'update', 'delete', 'manage', 'execute');

-- ============================================================
-- ORGANIZATIONS
-- ============================================================
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    domain VARCHAR(255),
    logo_url TEXT,
    plan VARCHAR(50) NOT NULL DEFAULT 'enterprise',
    settings JSONB NOT NULL DEFAULT '{}',
    features JSONB NOT NULL DEFAULT '{}',
    max_customers INTEGER NOT NULL DEFAULT 100000,
    max_users INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT true,
    trial_ends_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_plan ON organizations(plan);
CREATE INDEX idx_organizations_active ON organizations(is_active) WHERE is_active = true;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    avatar_url TEXT,
    job_title VARCHAR(255),
    department VARCHAR(100),
    phone VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    mfa_enabled BOOLEAN NOT NULL DEFAULT false,
    mfa_secret TEXT,
    last_login_at TIMESTAMPTZ,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    password_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, email)
);

CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(organization_id, is_active) WHERE is_active = true;

-- ============================================================
-- ROLES
-- ============================================================
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT false,
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, name)
);

CREATE INDEX idx_roles_org ON roles(organization_id);

-- ============================================================
-- PERMISSIONS
-- ============================================================
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    resource permission_resource NOT NULL,
    action permission_action NOT NULL,
    conditions JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(role_id, resource, action)
);

CREATE INDEX idx_permissions_role ON permissions(role_id);

-- ============================================================
-- USER ROLES (junction)
-- ============================================================
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES users(id),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);

-- ============================================================
-- CUSTOMERS
-- ============================================================
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(20),
    timezone VARCHAR(50) DEFAULT 'UTC',
    locale VARCHAR(10) DEFAULT 'en-US',
    location JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    custom_attributes JSONB DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_test BOOLEAN NOT NULL DEFAULT false,
    consent_marketing BOOLEAN NOT NULL DEFAULT false,
    consent_analytics BOOLEAN NOT NULL DEFAULT true,
    consent_profiling BOOLEAN NOT NULL DEFAULT false,
    data_retention_days INTEGER DEFAULT 730,
    source VARCHAR(50) DEFAULT 'api',
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, external_id),
    UNIQUE(organization_id, email)
);

CREATE INDEX idx_customers_org ON customers(organization_id);
CREATE INDEX idx_customers_email ON customers(organization_id, email);
CREATE INDEX idx_customers_external ON customers(organization_id, external_id);
CREATE INDEX idx_customers_active ON customers(organization_id, is_active) WHERE is_active = true;
CREATE INDEX idx_customers_consent ON customers(organization_id, consent_marketing) WHERE consent_marketing = true;
CREATE INDEX idx_customers_created ON customers(organization_id, created_at DESC);
CREATE INDEX idx_customers_tags ON customers USING GIN(tags);
CREATE INDEX idx_customers_attributes ON customers USING GIN(custom_attributes);

-- Partitioned customer events table (alternative for hash-partitioned access)
CREATE TABLE customers_partitioned (
    LIKE customers INCLUDING DEFAULTS INCLUDING IDENTITY INCLUDING GENERATED
) PARTITION BY HASH (id);
ALTER TABLE customers_partitioned ADD PRIMARY KEY (id, organization_id, email);
ALTER TABLE customers_partitioned ADD UNIQUE (organization_id, external_id, id);
ALTER TABLE customers_partitioned ADD UNIQUE (organization_id, email, id);

-- ============================================================
-- CUSTOMER PROFILES (1:1 with customers)
-- ============================================================
CREATE TABLE customer_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL UNIQUE REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title VARCHAR(100),
    company VARCHAR(255),
    industry VARCHAR(100),
    annual_revenue NUMERIC(15,2),
    employee_count INTEGER,
    website VARCHAR(500),
    linkedin_url TEXT,
    twitter_handle VARCHAR(100),
    bio TEXT,
    avatar_url TEXT,
    preferred_language VARCHAR(10) DEFAULT 'en',
    communication_style VARCHAR(50) DEFAULT 'formal',
    personality_traits JSONB DEFAULT '{}',
    psychographic_segment VARCHAR(100),
    enrichment_data JSONB DEFAULT '{}',
    enrichment_status VARCHAR(50) DEFAULT 'pending',
    last_enriched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customer_profiles_org ON customer_profiles(organization_id);
CREATE INDEX idx_customer_profiles_industry ON customer_profiles(organization_id, industry);

-- ============================================================
-- CUSTOMER TWINS (1:1 with customers)
-- ============================================================
CREATE TABLE customer_twins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL UNIQUE REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    status twin_status NOT NULL DEFAULT 'building',
    version INTEGER NOT NULL DEFAULT 1,
    behavior_profile JSONB NOT NULL DEFAULT '{}',
    interest_graph JSONB NOT NULL DEFAULT '{}',
    channel_affinity JSONB NOT NULL DEFAULT '{}',
    engagement_score DOUBLE PRECISION DEFAULT 0.0,
    loyalty_score DOUBLE PRECISION DEFAULT 0.0,
    lifetime_value DOUBLE PRECISION DEFAULT 0.0,
    sentiment_trend DOUBLE PRECISION[] DEFAULT '{}',
    intent_forecast JSONB NOT NULL DEFAULT '{}',
    risk_indicators JSONB NOT NULL DEFAULT '{}',
    communication_preferences JSONB NOT NULL DEFAULT '{}',
    embedding_id UUID,
    last_event_at TIMESTAMPTZ,
    last_prediction_at TIMESTAMPTZ,
    twin_metadata JSONB NOT NULL DEFAULT '{}',
    confidence_score DOUBLE PRECISION DEFAULT 0.0,
    staleness_score DOUBLE PRECISION DEFAULT 0.0,
    recalculation_required BOOLEAN NOT NULL DEFAULT false,
    built_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customer_twins_org ON customer_twins(organization_id);
CREATE INDEX idx_customer_twins_status ON customer_twins(organization_id, status);
CREATE INDEX idx_customer_twins_engagement ON customer_twins(organization_id, engagement_score DESC);
CREATE INDEX idx_customer_twins_loyalty ON customer_twins(organization_id, loyalty_score DESC);
CREATE INDEX idx_customer_twins_ltv ON customer_twins(organization_id, lifetime_value DESC);
CREATE INDEX idx_customer_twins_recalc ON customer_twins(organization_id, recalculation_required) WHERE recalculation_required = true;
CREATE INDEX idx_customer_twins_stale ON customer_twins(organization_id, staleness_score DESC);
CREATE INDEX idx_customer_twins_behavior ON customer_twins USING GIN(behavior_profile);
CREATE INDEX idx_customer_twins_interest ON customer_twins USING GIN(interest_graph);

-- ============================================================
-- CUSTOMER EVENTS (partitioned)
-- ============================================================
CREATE TABLE customer_events (
    id UUID DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    session_id UUID,
    event_type event_type NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    event_properties JSONB NOT NULL DEFAULT '{}',
    context JSONB NOT NULL DEFAULT '{}',
    channel VARCHAR(50),
    source VARCHAR(50),
    device_type VARCHAR(100),
    device_os VARCHAR(100),
    browser VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    referrer TEXT,
    url TEXT,
    geolocation JSONB DEFAULT '{}',
    campaign_id UUID,
    value DOUBLE PRECISION,
    currency VARCHAR(3),
    processed BOOLEAN NOT NULL DEFAULT false,
    processing_latency_ms INTEGER,
    event_timestamp TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, event_timestamp)
) PARTITION BY RANGE (event_timestamp);

-- Create monthly partitions
CREATE TABLE customer_events_2026_01 PARTITION OF customer_events
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE customer_events_2026_02 PARTITION OF customer_events
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE customer_events_2026_03 PARTITION OF customer_events
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE customer_events_2026_04 PARTITION OF customer_events
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE customer_events_2026_05 PARTITION OF customer_events
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE customer_events_2026_06 PARTITION OF customer_events
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE customer_events_2026_07 PARTITION OF customer_events
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE customer_events_2026_08 PARTITION OF customer_events
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE customer_events_2026_09 PARTITION OF customer_events
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE customer_events_2026_10 PARTITION OF customer_events
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE customer_events_2026_11 PARTITION OF customer_events
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE customer_events_2026_12 PARTITION OF customer_events
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

-- Default partition for future dates
CREATE TABLE customer_events_default PARTITION OF customer_events
    FOR VALUES FROM ('2027-01-01') TO ('2030-01-01');

CREATE INDEX idx_events_org_customer ON customer_events(organization_id, customer_id);
CREATE INDEX idx_events_type ON customer_events(organization_id, event_type, event_timestamp DESC);
CREATE INDEX idx_events_timestamp ON customer_events(organization_id, event_timestamp DESC);
CREATE INDEX idx_events_session ON customer_events(session_id);
CREATE INDEX idx_events_unprocessed ON customer_events(organization_id, processed) WHERE processed = false;
CREATE INDEX idx_events_properties ON customer_events USING GIN(event_properties);
CREATE INDEX idx_events_context ON customer_events USING GIN(context);

-- ============================================================
-- CUSTOMER SESSIONS
-- ============================================================
CREATE TABLE customer_sessions (
    id UUID DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    session_start TIMESTAMPTZ NOT NULL,
    session_end TIMESTAMPTZ,
    duration_seconds INTEGER,
    page_views INTEGER DEFAULT 0,
    events_count INTEGER DEFAULT 0,
    channel VARCHAR(50),
    device_type VARCHAR(100),
    device_os VARCHAR(100),
    browser VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    referrer TEXT,
    landing_url TEXT,
    exit_url TEXT,
    is_bounce BOOLEAN DEFAULT false,
    utm_source VARCHAR(255),
    utm_medium VARCHAR(255),
    utm_campaign VARCHAR(255),
    utm_content VARCHAR(255),
    utm_term VARCHAR(255),
    session_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, session_start)
) PARTITION BY RANGE (session_start);

CREATE TABLE customer_sessions_2026_01 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE customer_sessions_2026_02 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE customer_sessions_2026_03 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE customer_sessions_2026_04 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE customer_sessions_2026_05 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE customer_sessions_2026_06 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE customer_sessions_2026_07 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE customer_sessions_2026_08 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE customer_sessions_2026_09 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE customer_sessions_2026_10 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE customer_sessions_2026_11 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE customer_sessions_2026_12 PARTITION OF customer_sessions
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');
CREATE TABLE customer_sessions_default PARTITION OF customer_sessions
    FOR VALUES FROM ('2027-01-01') TO ('2030-01-01');

CREATE INDEX idx_sessions_org_customer ON customer_sessions(organization_id, customer_id);
CREATE INDEX idx_sessions_start ON customer_sessions(organization_id, session_start DESC);
CREATE INDEX idx_sessions_channel ON customer_sessions(organization_id, channel);

-- ============================================================
-- CUSTOMER PREFERENCES
-- ============================================================
CREATE TABLE customer_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    channel_email BOOLEAN NOT NULL DEFAULT true,
    channel_sms BOOLEAN NOT NULL DEFAULT false,
    channel_push BOOLEAN NOT NULL DEFAULT true,
    channel_in_app BOOLEAN NOT NULL DEFAULT true,
    email_frequency VARCHAR(20) DEFAULT 'daily',
    sms_frequency VARCHAR(20) DEFAULT 'weekly',
    push_frequency VARCHAR(20) DEFAULT 'realtime',
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    timezone VARCHAR(50) DEFAULT 'UTC',
    preferred_categories TEXT[] DEFAULT '{}',
    preferred_brands TEXT[] DEFAULT '{}',
    excluded_categories TEXT[] DEFAULT '{}',
    max_communications_per_day INTEGER DEFAULT 5,
    do_not_disturb BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(customer_id)
);

CREATE INDEX idx_preferences_org ON customer_preferences(organization_id);
CREATE INDEX idx_preferences_channels ON customer_preferences(organization_id, channel_email, channel_sms, channel_push);
CREATE INDEX idx_preferences_categories ON customer_preferences USING GIN(preferred_categories);
CREATE INDEX idx_preferences_dnd ON customer_preferences(organization_id, do_not_disturb) WHERE do_not_disturb = false;

-- ============================================================
-- CUSTOMER INTERESTS
-- ============================================================
CREATE TABLE customer_interests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    category VARCHAR(255) NOT NULL,
    subcategory VARCHAR(255),
    interest_level DOUBLE PRECISION NOT NULL DEFAULT 0.0 CHECK (interest_level >= 0 AND interest_level <= 1),
    affinity_score DOUBLE PRECISION NOT NULL DEFAULT 0.0 CHECK (affinity_score >= 0 AND affinity_score <= 1),
    interaction_count INTEGER NOT NULL DEFAULT 0,
    last_interaction_at TIMESTAMPTZ,
    first_detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT true,
    decay_factor DOUBLE PRECISION DEFAULT 0.05,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(customer_id, category, subcategory)
);

CREATE INDEX idx_interests_org ON customer_interests(organization_id);
CREATE INDEX idx_interests_level ON customer_interests(organization_id, interest_level DESC);
CREATE INDEX idx_interests_category ON customer_interests(organization_id, category);

-- ============================================================
-- CUSTOMER EMBEDDINGS
-- ============================================================
CREATE TABLE customer_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL UNIQUE REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'bge-large-en-v1.5',
    embedding_dimensions INTEGER NOT NULL DEFAULT 1024,
    embedding_vector DOUBLE PRECISION[] NOT NULL,
    metadata JSONB DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_embeddings_org ON customer_embeddings(organization_id);
CREATE INDEX idx_embeddings_model ON customer_embeddings(embedding_model);

-- ============================================================
-- CUSTOMER PREDICTIONS
-- ============================================================
CREATE TABLE customer_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    prediction_type prediction_target NOT NULL,
    prediction_value DOUBLE PRECISION NOT NULL,
    prediction_probability DOUBLE PRECISION,
    prediction_label VARCHAR(255),
    prediction_explanation JSONB DEFAULT '{}',
    feature_importance JSONB DEFAULT '{}',
    confidence_score DOUBLE PRECISION DEFAULT 0.0,
    model_version VARCHAR(100) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    input_features JSONB DEFAULT '{}',
    valid_until TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_predictions_org ON customer_predictions(organization_id);
CREATE INDEX idx_predictions_customer ON customer_predictions(organization_id, customer_id, prediction_type);
CREATE INDEX idx_predictions_type ON customer_predictions(organization_id, prediction_type, prediction_value DESC);
CREATE INDEX idx_predictions_active ON customer_predictions(organization_id, is_active) WHERE is_active = true;
CREATE INDEX idx_predictions_model ON customer_predictions(model_name, model_version);

-- ============================================================
-- CUSTOMER SEGMENTS
-- ============================================================
CREATE TABLE customer_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source segment_source NOT NULL,
    rules JSONB DEFAULT '{}',
    ml_model_id VARCHAR(255),
    cluster_id INTEGER,
    customer_count INTEGER NOT NULL DEFAULT 0,
    segment_metadata JSONB DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_dynamic BOOLEAN NOT NULL DEFAULT true,
    refresh_interval_minutes INTEGER DEFAULT 60,
    last_refreshed_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, name)
);

CREATE INDEX idx_segments_org ON customer_segments(organization_id);
CREATE INDEX idx_segments_source ON customer_segments(organization_id, source);
CREATE INDEX idx_segments_active ON customer_segments(organization_id, is_active) WHERE is_active = true;

-- ============================================================
-- CUSTOMER SEGMENT MAPPING (junction)
-- ============================================================
CREATE TABLE customer_segment_mapping (
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    segment_id UUID NOT NULL REFERENCES customer_segments(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by VARCHAR(50) DEFAULT 'system',
    score DOUBLE PRECISION DEFAULT 1.0,
    PRIMARY KEY (customer_id, segment_id)
);

CREATE INDEX idx_csm_segment ON customer_segment_mapping(segment_id);
CREATE INDEX idx_csm_customer ON customer_segment_mapping(customer_id);
CREATE INDEX idx_csm_org ON customer_segment_mapping(organization_id);

-- ============================================================
-- CAMPAIGNS
-- ============================================================
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    goal VARCHAR(255),
    status campaign_status NOT NULL DEFAULT 'draft',
    channel notification_channel NOT NULL,
    segments JSONB DEFAULT '[]',
    target_customers TEXT[] DEFAULT '{}',
    exclude_customers TEXT[] DEFAULT '{}',
    content JSONB NOT NULL DEFAULT '{}',
    schedule JSONB DEFAULT '{}',
    budget NUMERIC(15,2),
    expected_reach INTEGER,
    expected_conversion_rate DOUBLE PRECISION,
    ab_test_config JSONB DEFAULT '{}',
    frequency_cap INTEGER DEFAULT 3,
    frequency_cap_period VARCHAR(20) DEFAULT 'day',
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_campaigns_org ON campaigns(organization_id);
CREATE INDEX idx_campaigns_status ON campaigns(organization_id, status);
CREATE INDEX idx_campaigns_type ON campaigns(organization_id, type);
CREATE INDEX idx_campaigns_schedule ON campaigns(organization_id, start_at, end_at);
CREATE INDEX idx_campaigns_channel ON campaigns(organization_id, channel);

-- ============================================================
-- CAMPAIGN TARGETS
-- ============================================================
CREATE TABLE campaign_targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    segment_id UUID REFERENCES customer_segments(id),
    treatment VARCHAR(50) DEFAULT 'control',
    score DOUBLE PRECISION,
    priority INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    converted_at TIMESTAMPTZ,
    revenue NUMERIC(15,2),
    engagement_score DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(campaign_id, customer_id)
);

CREATE INDEX idx_campaign_targets_campaign ON campaign_targets(campaign_id);
CREATE INDEX idx_campaign_targets_customer ON campaign_targets(organization_id, customer_id);
CREATE INDEX idx_campaign_targets_status ON campaign_targets(campaign_id, status);
CREATE INDEX idx_campaign_targets_treatment ON campaign_targets(campaign_id, treatment);

-- ============================================================
-- CAMPAIGN RESULTS
-- ============================================================
CREATE TABLE campaign_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    total_targeted INTEGER NOT NULL DEFAULT 0,
    total_delivered INTEGER NOT NULL DEFAULT 0,
    total_opened INTEGER NOT NULL DEFAULT 0,
    total_clicked INTEGER NOT NULL DEFAULT 0,
    total_converted INTEGER NOT NULL DEFAULT 0,
    total_revenue NUMERIC(15,2) DEFAULT 0.0,
    total_cost NUMERIC(15,2) DEFAULT 0.0,
    open_rate DOUBLE PRECISION DEFAULT 0.0,
    click_rate DOUBLE PRECISION DEFAULT 0.0,
    conversion_rate DOUBLE PRECISION DEFAULT 0.0,
    bounce_rate DOUBLE PRECISION DEFAULT 0.0,
    unsubscribe_rate DOUBLE PRECISION DEFAULT 0.0,
    roi DOUBLE PRECISION DEFAULT 0.0,
    engagement_distribution JSONB DEFAULT '{}',
    channel_performance JSONB DEFAULT '{}',
    segment_performance JSONB DEFAULT '{}',
    hourly_breakdown JSONB DEFAULT '{}',
    daily_breakdown JSONB DEFAULT '{}',
    ab_test_results JSONB DEFAULT '{}',
    control_group_results JSONB DEFAULT '{}',
    treatment_group_results JSONB DEFAULT '{}',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(campaign_id)
);

CREATE INDEX idx_campaign_results_org ON campaign_results(organization_id);

-- ============================================================
-- SIMULATIONS
-- ============================================================
CREATE TABLE simulations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL DEFAULT 'campaign',
    status simulation_status NOT NULL DEFAULT 'draft',
    campaign_id UUID REFERENCES campaigns(id),
    configuration JSONB NOT NULL DEFAULT '{}',
    parameters JSONB NOT NULL DEFAULT '{}',
    agent_configuration JSONB NOT NULL DEFAULT '{}',
    monte_carlo_iterations INTEGER DEFAULT 1000,
    confidence_level DOUBLE PRECISION DEFAULT 0.95,
    time_horizon_days INTEGER DEFAULT 30,
    segment_ids TEXT[] DEFAULT '{}',
    sample_size INTEGER DEFAULT 10000,
    include_control BOOLEAN NOT NULL DEFAULT true,
    expected_outputs TEXT[] DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_simulations_org ON simulations(organization_id);
CREATE INDEX idx_simulations_status ON simulations(organization_id, status);
CREATE INDEX idx_simulations_campaign ON simulations(campaign_id);

-- ============================================================
-- SIMULATION RUNS
-- ============================================================
CREATE TABLE simulation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id UUID NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    run_number INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    seed INTEGER,
    agents_count INTEGER DEFAULT 0,
    iterations_executed INTEGER DEFAULT 0,
    runtime_seconds DOUBLE PRECISION,
    cpu_usage DOUBLE PRECISION,
    memory_usage_bytes BIGINT,
    error_message TEXT,
    logs TEXT[] DEFAULT '{}',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(simulation_id, run_number)
);

CREATE INDEX idx_simulation_runs_sim ON simulation_runs(simulation_id);
CREATE INDEX idx_simulation_runs_status ON simulation_runs(simulation_id, status);

-- ============================================================
-- SIMULATION RESULTS
-- ============================================================
CREATE TABLE simulation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id UUID NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    run_id UUID REFERENCES simulation_runs(id),
    aggregated_metrics JSONB NOT NULL DEFAULT '{}',
    customer_projections JSONB NOT NULL DEFAULT '{}',
    segment_projections JSONB NOT NULL DEFAULT '{}',
    campaign_impact JSONB NOT NULL DEFAULT '{}',
    confidence_intervals JSONB NOT NULL DEFAULT '{}',
    monte_carlo_distribution JSONB NOT NULL DEFAULT '{}',
    expected_outcomes JSONB NOT NULL DEFAULT '{}',
    risk_assessment JSONB DEFAULT '{}',
    recommendations TEXT[] DEFAULT '{}',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(simulation_id, run_id)
);

CREATE INDEX idx_simulation_results_sim ON simulation_results(simulation_id);
CREATE INDEX idx_simulation_results_org ON simulation_results(organization_id);

-- ============================================================
-- RECOMMENDATIONS
-- ============================================================
CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    rank INTEGER NOT NULL DEFAULT 0,
    category VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    is_actionable BOOLEAN NOT NULL DEFAULT true,
    is_applied BOOLEAN NOT NULL DEFAULT false,
    applied_at TIMESTAMPTZ,
    source VARCHAR(50),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recommendations_customer ON recommendations(organization_id, customer_id);
CREATE INDEX idx_recommendations_type ON recommendations(organization_id, type, score DESC);
CREATE INDEX idx_recommendations_applied ON recommendations(organization_id, is_applied) WHERE is_applied = false;
CREATE INDEX idx_recommendations_rank ON recommendations(organization_id, rank);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    channel notification_channel NOT NULL,
    status notification_status NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    template_id VARCHAR(255),
    template_data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    campaign_id UUID REFERENCES campaigns(id),
    scheduled_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    failure_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_org ON notifications(organization_id);
CREATE INDEX idx_notifications_customer ON notifications(organization_id, customer_id);
CREATE INDEX idx_notifications_status ON notifications(organization_id, status);
CREATE INDEX idx_notifications_channel ON notifications(organization_id, channel);
CREATE INDEX idx_notifications_schedule ON notifications(organization_id, scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX idx_notifications_retry ON notifications(organization_id, status) WHERE status = 'failed' AND retry_count < max_retries;

-- ============================================================
-- AUDIT LOGS
-- ============================================================
CREATE TABLE audit_logs (
    id UUID DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id UUID,
    actor_type VARCHAR(50) NOT NULL DEFAULT 'user',
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    resource_data JSONB DEFAULT '{}',
    changes JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    request_id UUID,
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE audit_logs_2026_02 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE audit_logs_2026_03 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE audit_logs_2026_04 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE audit_logs_2026_05 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE audit_logs_2026_06 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE audit_logs_2026_07 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE audit_logs_2026_08 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE audit_logs_2026_09 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE audit_logs_2026_10 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE audit_logs_2026_11 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE audit_logs_2026_12 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');
CREATE TABLE audit_logs_default PARTITION OF audit_logs
    FOR VALUES FROM ('2027-01-01') TO ('2030-01-01');

CREATE INDEX idx_audit_org ON audit_logs(organization_id);
CREATE INDEX idx_audit_actor ON audit_logs(organization_id, actor_id);
CREATE INDEX idx_audit_action ON audit_logs(organization_id, action);
CREATE INDEX idx_audit_resource ON audit_logs(organization_id, resource_type, resource_id);
CREATE INDEX idx_audit_created ON audit_logs(organization_id, created_at DESC);

-- ============================================================
-- TRIGGER FUNCTIONS
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER trg_organizations_updated_at
    BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_customer_profiles_updated_at
    BEFORE UPDATE ON customer_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_customer_twins_updated_at
    BEFORE UPDATE ON customer_twins FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_customer_preferences_updated_at
    BEFORE UPDATE ON customer_preferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_customer_interests_updated_at
    BEFORE UPDATE ON customer_interests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_customer_embeddings_updated_at
    BEFORE UPDATE ON customer_embeddings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_campaigns_updated_at
    BEFORE UPDATE ON campaigns FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_simulations_updated_at
    BEFORE UPDATE ON simulations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_customer_segments_updated_at
    BEFORE UPDATE ON customer_segments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- EVENT TOUCH TRIGGER
-- ============================================================
CREATE OR REPLACE FUNCTION update_customer_last_seen()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE customers
    SET last_seen_at = NEW.event_timestamp
    WHERE id = NEW.customer_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_customer_last_seen
    AFTER INSERT ON customer_events
    FOR EACH ROW EXECUTE FUNCTION update_customer_last_seen();

-- ============================================================
-- ROW-LEVEL SECURITY
-- ============================================================
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_twins ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_interests ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulations ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Organization-level isolation policy
CREATE POLICY org_isolation ON customers
    USING (organization_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation ON customer_events
    USING (organization_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation ON customer_twins
    USING (organization_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation ON customer_profiles
    USING (organization_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation ON customer_preferences
    USING (organization_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation ON customer_interests
    USING (organization_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation ON customer_embeddings
    USING (organization_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation ON customer_predictions
    USING (organization_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation ON customer_segments
    USING (organization_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation ON campaigns
    USING (organization_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation ON simulations
    USING (organization_id = current_setting('app.current_org_id')::UUID);

-- ============================================================
-- MAINTENANCE QUERIES (comment for reference)
-- ============================================================
-- Refresh materialized view for performance:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_customer_summary;

-- Reindex partitioned tables monthly:
-- REINDEX TABLE customer_events;
-- REINDEX TABLE customer_sessions;
-- REINDEX TABLE audit_logs;

-- Update statistics:
-- ANALYZE customers;
-- ANALYZE customer_events;
-- ANALYZE customer_twins;
