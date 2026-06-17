# Machine Learning System Design

## 1. Customer Segmentation

```python
"""
Model Type: Unsupervised clustering (HDBSCAN + KMeans ensemble)
Training Frequency: Daily
Features Used:
  - Behavioral: session_freq, avg_session_dur, page_depth, bounce_rate
  - Purchase: purchase_freq, aov, category_diversity, discount_usage
  - Engagement: email_engagement, push_engagement, channel_preference
  - Lifecycle: days_since_first_seen, days_since_last_purchase, rfm_scores
  - Profile: age_group, location_tier, device_type

Pipeline:
  1. Feature extraction from customer_twins + customer_events (90d window)
  2. StandardScaler normalization
  3. PCA (n_components=50) dimensionality reduction
  4. HDBSCAN (min_cluster_size=100, min_samples=20) 
  5. KMeans (k=8-15, determined by elbow method)
  6. Ensemble: weighted combination of both cluster assignments
  7. Segment labeling via centroid analysis

Storage:
  - Segment definitions -> customer_segments table
  - Customer-segment mapping -> customer_segment_mapping table
  - Cluster centroids -> MLflow artifacts
  - Model artifacts -> MLflow model registry

Monitoring:
  - Silhouette score (> 0.3 threshold)
  - Davies-Bouldin index (< 1.5 threshold)
  - Segment stability (Jaccard similarity between runs)
  - Segment size distribution (no dominant segment > 40%)
"""

# Training pipeline pseudocode
class CustomerSegmentationTrainer:
    def __init__(self):
        self.feature_columns = [
            'session_freq_weekly', 'avg_session_dur', 'page_depth_avg', 'bounce_rate',
            'purchase_freq_monthly', 'avg_order_value', 'category_diversity', 'discount_sensitivity',
            'email_open_rate', 'email_click_rate', 'push_opt_in',
            'days_since_first_seen', 'days_since_last_purchase',
            'rfm_recency', 'rfm_frequency', 'rfm_monetary',
            'engagement_score', 'loyalty_score', 'lifetime_value',
            'device_type_encoded', 'channel_preference_encoded',
        ]
        self.n_clusters = 10
        
    def train(self, df: pd.DataFrame):
        X = df[self.feature_columns].fillna(0)
        
        # Normalize
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # PCA
        pca = PCA(n_components=50, random_state=42)
        X_pca = pca.fit_transform(X_scaled)
        
        # HDBSCAN
        clusterer = HDBSCAN(
            min_cluster_size=100,
            min_samples=20,
            metric='euclidean',
            prediction_data=True,
        )
        hdbscan_labels = clusterer.fit_predict(X_pca)
        
        # KMeans
        kmeans = KMeans(
            n_clusters=self.n_clusters,
            random_state=42,
            n_init=10,
        )
        kmeans_labels = kmeans.fit_predict(X_pca)
        
        # Ensemble (weighted average)
        ensemble_labels = self.ensemble_clusters(hdbscan_labels, kmeans_labels)
        
        # Label segments
        segment_labels = self.label_segments(X, ensemble_labels, pca, kmeans)
        
        return ensemble_labels, segment_labels, {
            'scaler': scaler,
            'pca': pca,
            'hdbscan': clusterer,
            'kmeans': kmeans,
            'segment_labels': segment_labels,
        }
```

## 2. Churn Prediction

```python
"""
Model: LightGBM + XGBoost ensemble (Stacking)
Task: Binary classification (will churn in next 30 days)
Training Frequency: Weekly
Positive Class: Customers who churned (no activity for 30+ days + negative indicators)

Features (45 total):
  Engagement Features (15):
    - days_since_last_visit, days_since_last_email_open
    - session_freq_change_7d, session_freq_change_30d
    - avg_session_dur_change, page_depth_change
    - bounce_rate_trend, email_open_rate_trend
    - support_ticket_count_30d
  
  Purchase Features (10):
    - days_since_last_purchase, purchase_freq_change
    - aov_change, category_change_count
    - discount_usage_rate, refund_rate
    - cart_abandonment_rate_30d
  
  Sentiment Features (8):
    - avg_sentiment_7d, avg_sentiment_30d
    - sentiment_trend (slope over 30d)
    - negative_feedback_count
    - complaint_count_30d
  
  Profile Features (7):
    - account_age_days, lifecycle_stage_encoded
    - loyalty_score, engagement_score_change
    - communication_preference_change
  
  Interaction Features (5):
    - channel_engagement_change
    - content_affinity_change
    - time_to_response_change

Training:
  1. Extract 90-day window for features, label next 30 days
  2. Handle class imbalance (SMOTE + class weights)
  3. LightGBM: n_estimators=1000, learning_rate=0.01, num_leaves=64
  4. XGBoost: n_estimators=1000, learning_rate=0.01, max_depth=8
  5. Stacking meta-model: LogisticRegression
  6. Hyperparameter optimization: Optuna (100 trials)
  7. Feature importance analysis
  8. SHAP explanations for predictions

Evaluation:
  - AUC-ROC > 0.85
  - Precision@10% > 0.70
  - Recall@20% > 0.80
  - F1 Score > 0.65
  - Lift at 10% > 3.0

Inference:
  - Real-time: Event triggers churn prediction
  - Batch: Nightly scoring for all customers
  - Output: churn_probability (0-1), risk_level (low/medium/high/critical)
  - Triggers: Risk level changes trigger alerts and actions

Model Registry:
  mlflow:
    experiment: twin-cx-churn-prediction
    model_name: churn_ensemble_v1
    stage: production
"""

class ChurnPredictor:
    def __init__(self, model_path: str):
        self.lgb_model = lightgbm.Booster(model_file=f"{model_path}/lgb_model.txt")
        self.xgb_model = xgboost.Booster(model_file=f"{model_path}/xgb_model.json")
        self.meta_model = joblib.load(f"{model_path}/meta_model.pkl")
        self.scaler = joblib.load(f"{model_path}/scaler.pkl")
        self.feature_columns = joblib.load(f"{model_path}/feature_columns.pkl")
    
    def predict_proba(self, features: np.ndarray) -> float:
        X = self.scaler.transform(features.reshape(1, -1))
        lgb_pred = self.lgb_model.predict(X)[0]
        xgb_pred = self.xgb_model.predict(xgboost.DMatrix(X))[0]
        stacked = np.column_stack([lgb_pred, xgb_pred])
        return self.meta_model.predict_proba(stacked)[0][1]
    
    def get_risk_level(self, probability: float) -> str:
        if probability >= 0.7: return 'critical'
        if probability >= 0.5: return 'high'
        if probability >= 0.3: return 'medium'
        return 'low'
    
    def explain_prediction(self, features: np.ndarray) -> dict:
        import shap
        X = self.scaler.transform(features.reshape(1, -1))
        explainer = shap.TreeExplainer(self.lgb_model)
        shap_values = explainer.shap_values(X)
        
        feature_importance = list(zip(self.feature_columns, shap_values[0]))
        feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)
        
        return {
            'top_features': feature_importance[:10],
            'expected_value': explainer.expected_value,
        }
```

## 3. Intent Prediction

```python
"""
Model: PyTorch Transformer (fine-tuned BART)
Task: Multi-label classification of customer intent
Intents: ['purchase', 'browse', 'compare', 'research', 'support', 'cancel', 'upgrade', 'downgrade', 'refer', 'churn']
Training Frequency: Weekly

Architecture:
  - Base: facebook/bart-base
  - Classification head: 768 -> 256 -> 10 (with dropout=0.3)
  - Training: Mixed precision, gradient accumulation

Features:
  - Text: event descriptions, page titles, search queries, support ticket content
  - Context: time of day, device, channel, session history
  - Behavioral: recent events sequence (last 20 actions)

Training Pipeline:
  1. Collect event sequences with labeled intents
  2. Tokenize with BART tokenizer (max_length=128)
  3. Train with cross-entropy loss + label smoothing
  4. Evaluate on held-out test set
  5. Export to TorchScript for production inference

Monitoring:
  - Log loss, accuracy per intent
  - Confusion matrix drift
  - Calibration error
  - Inference latency (target < 50ms)
"""

class IntentClassifier(nn.Module):
    def __init__(self, num_intents=10):
        super().__init__()
        self.bart = BartForSequenceClassification.from_pretrained(
            'facebook/bart-base',
            num_labels=num_intents,
            problem_type="multi_label_classification"
        )
        self.dropout = nn.Dropout(0.3)
        
    def forward(self, input_ids, attention_mask, labels=None):
        outputs = self.bart(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
        )
        return outputs
```

## 4. Recommendation Engine

```python
"""
Model: Hybrid (Collaborative + Content-based + LLM)
Approach: Two-stage (Candidate generation + Ranking)

Stage 1: Candidate Generation
  - Collaborative: Matrix Factorization (ALS)
  - Content-based: Qdrant similarity (product embeddings)
  - Popularity: Trending in segment
  - Candidates: 200 per customer

Stage 2: Ranking
  - Features: customer_embedding || product_embedding || cross_features
  - Model: LightGBM LambdaRank
  - Training: Implicit feedback (views, clicks, purchases)
  - Output: Ranked list of 20 recommendations

Features:
  - Customer: embedding (1024d), engagement score, loyalty score
  - Product: embedding (1024d), price, category, popularity
  - Cross: customer-product affinity, category affinity, price fit
  - Context: time of day, device, channel, session
  
Inference Pipeline:
  1. Retrieve candidates from Qdrant (200)
  2. Compute ranking features
  3. Score with LightGBM ranker
  4. Apply business rules (diversity, freshness, exclusion)
  5. Return top 20 recommendations
"""

class RecommendationService:
    def __init__(self):
        self.ranker = lightgbm.Booster(model_file="models/lambdarank_v2.txt")
        self.qdrant = QdrantClient()
        self.model_client = EmbeddingClient()
    
    async def get_recommendations(
        self,
        org_id: UUID,
        customer_id: UUID,
        limit: int = 20,
        context: dict | None = None,
    ) -> list[dict]:
        # 1. Get customer embedding
        customer_emb = await self.qdrant.search(
            collection_name="customer_embeddings",
            query_filter=Filter(
                must=[
                    FieldCondition(key="organization_id", match=MatchValue(value=str(org_id))),
                    FieldCondition(key="customer_id", match=MatchValue(value=str(customer_id))),
                ]
            ),
            limit=1,
        )
        
        if not customer_emb:
            return await self._popular_fallback(org_id, limit)
        
        # 2. Get product candidates from Qdrant
        candidates = await self.qdrant.search(
            collection_name="product_embeddings",
            query_vector=customer_emb[0].vector,
            query_filter=Filter(
                must=[
                    FieldCondition(key="organization_id", match=MatchValue(value=str(org_id))),
                    FieldCondition(key="is_active", match=MatchValue(value=True)),
                ]
            ),
            limit=200,
        )
        
        # 3. Compute ranking features
        features = []
        for c in candidates:
            feat = await self._compute_ranking_features(
                customer_emb[0].payload,
                c.payload,
                context,
            )
            features.append(feat)
        
        # 4. Rank candidates
        X = pd.DataFrame(features)
        scores = self.ranker.predict(X)
        
        # 5. Apply diversity and return
        ranked = list(zip(candidates, scores))
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return self._apply_diversity(ranked, limit)
```

## 5. Engagement Forecasting

```python
"""
Model: Prophet + LSTM ensemble
Task: Time series forecasting of engagement metrics
Forecast Horizon: 7/14/30/90 days
Metrics: session_count, email_opens, page_views, engagement_score

Prophet Component:
  - Seasonality: daily, weekly, yearly
  - Holiday effects
  - Changepoint detection
  - Uncertainty intervals

LSTM Component:
  - Input: 90-day history of engagement metrics
  - Architecture: 2 layers (128, 64) + Dropout(0.2) + Dense(1)
  - Lookback: 30 days
  - Output: 7-day forecast

Ensemble:
  - Weighted average of Prophet and LSTM predictions
  - Weights dynamically adjusted based on recent performance
  - Confidence intervals from Prophet + bootstrap

Monitoring:
  - MAPE < 20%
  - Coverage of confidence intervals > 80%
  - Prediction error by segment
  - Retrain trigger: MAPE > 25% for 3 consecutive days
"""
```

## 6. Drift Detection

```python
class DriftDetectionService:
    """
    Multi-dimensional drift detection:
    
    1. Data Drift:
       - Feature distribution (PSI > 0.2 threshold)
       - KS test on continuous features
       - Chi-squared on categorical features
    
    2. Model Drift:
       - Prediction distribution shift
       - Confidence score degradation
       - AUC drop on recent labeled data
    
    3. Concept Drift:
       - Feature-target relationship change
       - Segment composition change
       - Behavioral pattern shift
    
    Actions:
      - Alert: Send notification to ML team
      - Auto-rollback: Revert to previous model version
      - Auto-retrain: Trigger retraining pipeline
      - Shadow deploy: Deploy new model in shadow mode
    
    Monitoring Dashboard:
      - PSI chart over time
      - Feature importance change
      - Prediction drift by segment
      - Model performance over time
    """
    
    PSI_THRESHOLD = 0.2
    AUC_DROP_THRESHOLD = 0.05
    
    async def detect_feature_drift(
        self,
        model_name: str,
        model_version: str,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
    ) -> DriftReport:
        drifted_features = []
        
        for col in current_data.columns:
            if current_data[col].dtype in ['float64', 'int64']:
                # PSI calculation
                psi = self._calculate_psi(
                    reference_data[col],
                    current_data[col],
                )
                if psi > self.PSI_THRESHOLD:
                    drifted_features.append({
                        'feature': col,
                        'psi': psi,
                        'drift_type': 'continuous',
                    })
            else:
                # Chi-squared test
                chi2, p_value = chi2_contingency(
                    pd.crosstab(reference_data[col], current_data[col])
                )[:2]
                if p_value < 0.05:
                    drifted_features.append({
                        'feature': col,
                        'p_value': p_value,
                        'drift_type': 'categorical',
                    })
        
        return DriftReport(
            model_name=model_name,
            model_version=model_version,
            drifted_features=drifted_features,
            drift_detected=len(drifted_features) > 0,
            severity='high' if len(drifted_features) > 5 else 'medium' if len(drifted_features) > 2 else 'low',
            detected_at=datetime.utcnow(),
        )
```

## 7. Model Registry Architecture

```python
"""
MLflow Model Registry Structure:

experiment:
  twin-cx-segmentation/
  twin-cx-churn/
  twin-cx-intent/
  twin-cx-recommendation/
  twin-cx-engagement-forecast/

registered_models:
  churn_ensemble_v1/
    versions:
      v1: {stage: staging, metrics: {auc: 0.87, precision: 0.72, recall: 0.81}}
      v2: {stage: production, metrics: {auc: 0.89, precision: 0.74, recall: 0.83}}  # current
      v3: {stage: archived, metrics: {auc: 0.86, precision: 0.71, recall: 0.79}}
  
  segmentation_v2/
    versions:
      v1: {stage: production, metrics: {silhouette: 0.35, db_index: 1.2}}
  
  intent_classifier_v1/
    versions:
      v1: {stage: production, metrics: {accuracy: 0.82, f1: 0.79}}
  
  recommender_v2/
    versions:
      v1: {stage: production, metrics: {ndcg@10: 0.45, recall@20: 0.62}}

Artifacts per version:
  - model files (.pkl, .txt, .json, .pt)
  - feature_columns.pkl
  - scaler.pkl
  - config.yaml
  - metrics.json
  - feature_importance.png
  - confusion_matrix.png
  - shaps_summary.png

Transition Rules:
  - staging -> production: Manual approval + A/B test pass
  - production -> archived: Auto when new version promoted
  - production -> staging: Auto when drift detected
"""
```
