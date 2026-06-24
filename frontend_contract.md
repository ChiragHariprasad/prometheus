# TWINCX Frontend API Contract & Integration Guide

This document serves as the **single source of truth** for all frontend development. The frontend application must never assume routes or fields not explicitly documented here.

> [!IMPORTANT]
> **Backend Freeze Compliance**: This contract incorporates findings from the `BACKEND_FREEZE.md` audit. Review the [Backend Freeze Integration Alerts](#backend-freeze-integration-alerts) section first to avoid runtime mismatches.

## Backend Freeze Integration Alerts

These critical mismatches between backend implementations and frontend expectations were discovered during the audit:

1. **Recommendations Route Mismatch (UNSTABLE)**: 
   * *Route Mismatch*: The frontend calls `GET /api/v1/recommendations/{customer_id}`, but the backend implements `GET /api/v1/recommendations/{customer_id}/personalized`. Calling the frontend's current path will yield **404 Not Found**.
   * *Resolution*: Ensure frontend code is updated to `/api/v1/recommendations/{customer_id}/personalized`.
2. **Segment Compute Route Mismatch (CAUTION)**: 
   * *Route Mismatch*: The frontend calls `POST /api/v1/segments/{segment_id}/compute`, but the backend implements `POST /api/v1/segments/{segment_id}/refresh`. Calling the frontend path will yield **404 Not Found**.
   * *Resolution*: Update frontend trigger to `/api/v1/segments/{segment_id}/refresh`.
3. **Twin Scores Scale Mismatch (CAUTION)**: 
   * *Scale Mismatch*: The twin service returns scores (`engagement_score`, `loyalty_score`, `confidence_score`, `staleness_score`) scaled to `0.0 - 1.0` (e.g. `0.85`), but the UI gauge assumes a `0 - 100` range.
   * *Resolution*: Multiply twin service scores by `100` in the frontend before rendering them in the `ScoreGauge`.
4. **Digital Twin Missing Fields (CAUTION)**: 
   * *Missing Fields*: The `GET /api/v1/twins/{customer_id}` route uses a dictionary representation and omits `organization_id`, `lifetime_value`, and `version` fields. It returns `last_rebuilt` instead of `built_at` for build timestamps.
   * *Resolution*: Ensure frontend handles `undefined` values and maps `last_rebuilt` as the timestamp.
5. **sentiment_trend Schema Mismatch (CAUTION)**: 
   * *Type Mismatch*: Frontend defines `sentiment_trend` as `number[]`, but backend returns `[{"date": "day-0", "score": 0.8}, ...]`. 
   * *Resolution*: Frontend chart components must parse the object array format.
6. **Missing Administration Dashboard Endpoints (CAUTION)**: 
   * *Missing Endpoints*: The following endpoints will yield **404/405 Errors** as they are not implemented by the backend:
     - `PUT /api/v1/admin/feature-flags/{key}`
     - `GET /api/v1/admin/jobs`
     - `GET /api/v1/admin/rate-limits`
   * *Resolution*: Frontend must show disabled states or fallback banners for these pages.

---

## Global Error Patterns

The backend uses structured JSON error models. The frontend should handle these uniformly.

### Standard Application Error (400, 401, 403, 404, 409, 429, 503)
```json
{
  "success": false,
  "error": "Error details and user-friendly explanation",
  "error_code": "ERROR_CODE",
  "request_id": "8a9320dc-04c4-4cec-93aa-c5be074d760f"
}
```

### Form Validation Error (422 Unprocessable Entity)
```json
{
  "detail": [
    {
      "loc": [
        "body",
        "email"
      ],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## Dashboard

Contains endpoints driving dashboard functionalities, dashboards, data tables, and settings.

### List Api Keys
`GET` `/api/v1/admin/api-keys`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {}
]
```


* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Create Api Key
`POST` `/api/v1/admin/api-keys`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Delete Api Key
`DELETE` `/api/v1/admin/api-keys/{key_id}`

**Path Parameters**:
* `key_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show loading spinner on delete button, disable cancel button, and show confirmation modal block overlay.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### List Audit Logs
`GET` `/api/v1/admin/audit-logs`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "string",
      "user_id": "string",
      "user_name": "string",
      "action": "string",
      "resource": "string",
      "resource_id": "string",
      "details": {},
      "ip_address": "string",
      "timestamp": "2026-06-25T01:58:33Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Get Feature Flags
`GET` `/api/v1/admin/feature-flags`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "key": "string",
    "name": "string",
    "enabled": true,
    "description": "string"
  }
]
```


* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### List Admin Roles
`GET` `/api/v1/admin/roles`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {}
]
```


* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Get System Health
`GET` `/api/v1/admin/system-health`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "services": [
    {
      "name": "string",
      "status": "active",
      "latency": 0.85,
      "uptime": 0.85
    }
  ],
  "recent_errors": 1,
  "avg_response_time": 0.85,
  "requests_per_minute": 0.85
}
```

* **Required Response Fields**: `services`, `recent_errors`, `avg_response_time`, `requests_per_minute`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### List Admin Users
`GET` `/api/v1/admin/users`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "name": "string",
    "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "roles": [
      "string"
    ],
    "permissions": [
      "string"
    ]
  }
]
```


* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Delete Admin User
`DELETE` `/api/v1/admin/users/{user_id}`

**Path Parameters**:
* `user_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show loading spinner on delete button, disable cancel button, and show confirmation modal block overlay.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Update Admin User
`PUT` `/api/v1/admin/users/{user_id}`

**Path Parameters**:
* `user_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "name": "string",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "roles": [
    "string"
  ],
  "permissions": [
    "string"
  ]
}
```

* **Required Response Fields**: `id`, `email`, `first_name`, `last_name`, `organization_id`
* **Optional Response Fields**: `name`, `roles`, `permissions`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### List Webhooks
`GET` `/api/v1/admin/webhooks`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {}
]
```


* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Create Webhook
`POST` `/api/v1/admin/webhooks`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Delete Webhook
`DELETE` `/api/v1/admin/webhooks/{webhook_id}`

**Path Parameters**:
* `webhook_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show loading spinner on delete button, disable cancel button, and show confirmation modal block overlay.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Update Webhook
`PUT` `/api/v1/admin/webhooks/{webhook_id}`

**Path Parameters**:
* `webhook_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Get Dashboard
`GET` `/api/v1/analytics/dashboard`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "stats": {
    "total_customers": 1,
    "events_24h": 1,
    "active_campaigns": 1,
    "avg_engagement": 0.85,
    "total_revenue": 0.85,
    "revenue_growth": 0.85,
    "churn_rate": 0.85
  },
  "engagement_trend": [
    {}
  ],
  "revenue_data": [
    {}
  ],
  "segment_distribution": [
    {}
  ],
  "top_segments": [
    {}
  ],
  "recent_activity": [
    {}
  ],
  "churn_alerts": [
    {}
  ]
}
```

* **Required Response Fields**: `stats`
* **Optional Response Fields**: `engagement_trend`, `revenue_data`, `segment_distribution`, `top_segments`, `recent_activity`, `churn_alerts`

* **Loading State Handling**: Display skeleton loader cards (dashboard grid layout). Disable refresh button.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Login
`POST` `/api/v1/auth/login`

**Request Body Example**:
```json
{
  "email": "user@example.com",
  "password": "string",
  "mfa_code": null
}
```

* **Required Request Fields**: `email`, `password`
* **Optional Request Fields**: `mfa_code`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "string",
  "expires_in": 1,
  "user": {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "name": "string",
    "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "roles": [
      "string"
    ],
    "permissions": [
      "string"
    ]
  }
}
```

* **Required Response Fields**: `access_token`, `refresh_token`, `expires_in`, `user`
* **Optional Response Fields**: `token_type`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `400 Bad Request`

---

### Logout
`POST` `/api/v1/auth/logout`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Get Me
`GET` `/api/v1/auth/me`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "name": "string",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "roles": [
    "string"
  ],
  "permissions": [
    "string"
  ]
}
```

* **Required Response Fields**: `id`, `email`, `first_name`, `last_name`, `organization_id`
* **Optional Response Fields**: `name`, `roles`, `permissions`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Setup Mfa
`POST` `/api/v1/auth/mfa/setup`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "secret": "string",
  "qr_code_url": "string"
}
```

* **Required Response Fields**: `secret`, `qr_code_url`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `400 Bad Request`

---

### Verify Mfa
`POST` `/api/v1/auth/mfa/verify`

**Request Body Example**:
```json
{
  "code": "string"
}
```

* **Required Request Fields**: `code`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `400 Bad Request`

---

### Change Password
`POST` `/api/v1/auth/password-change`

**Request Body Example**:
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

* **Required Request Fields**: `current_password`, `new_password`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Request Password Reset
`POST` `/api/v1/auth/password-reset`

**Request Body Example**:
```json
{
  "email": "user@example.com"
}
```

* **Required Request Fields**: `email`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Confirm Password Reset
`POST` `/api/v1/auth/password-reset/confirm`

**Request Body Example**:
```json
{
  "token": "string",
  "new_password": "string"
}
```

* **Required Request Fields**: `token`, `new_password`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Refresh Token
`POST` `/api/v1/auth/refresh`

**Request Body Example**:
```json
{
  "refresh_token": "string"
}
```

* **Required Request Fields**: `refresh_token`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "string",
  "expires_in": 1
}
```

* **Required Response Fields**: `access_token`, `refresh_token`, `expires_in`
* **Optional Response Fields**: `token_type`

* **Loading State Handling**: Show global page blocker or dynamic progress bar toast. Disable target trigger button and display inline spinner.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Register
`POST` `/api/v1/auth/register`

**Request Body Example**:
```json
{
  "email": "user@example.com",
  "password": "string",
  "first_name": "string",
  "last_name": "string",
  "organization_name": "string"
}
```

* **Required Request Fields**: `email`, `password`, `first_name`, `last_name`, `organization_name`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "string",
  "expires_in": 1,
  "user": {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "name": "string",
    "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "roles": [
      "string"
    ],
    "permissions": [
      "string"
    ]
  }
}
```

* **Required Response Fields**: `access_token`, `refresh_token`, `expires_in`, `user`
* **Optional Response Fields**: `token_type`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `409 Conflict`

---

### List Notifications
`GET` `/api/v1/notifications`

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 
* `customer_id` (string) - *(Optional)* 
* `status` (string) - *(Optional)* 
* `channel` (string) - *(Optional)* 
* `sort_by` (string) - *(Optional)* 
* `sort_order` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "customer_id": null,
      "user_id": null,
      "type": "string",
      "title": "string",
      "body": "string",
      "channel": "string",
      "status": null,
      "priority": null,
      "campaign_id": null,
      "scheduled_at": null,
      "sent_at": null,
      "delivered_at": null,
      "opened_at": null,
      "clicked_at": null,
      "failed_at": null,
      "failure_reason": null,
      "retry_count": 1,
      "created_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Send Notification
`POST` `/api/v1/notifications`

**Request Body Example**:
```json
{
  "type": "string",
  "title": "string",
  "body": "string",
  "channel": "string",
  "customer_ids": [
    "string"
  ],
  "template_id": null,
  "template_data": {},
  "scheduled_at": null
}
```

* **Required Request Fields**: `type`, `title`, `body`, `channel`, `customer_ids`
* **Optional Request Fields**: `template_id`, `template_data`, `scheduled_at`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Get Notification Stats
`GET` `/api/v1/notifications/stats`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "total": 1,
  "sent": 1,
  "delivered": 1,
  "opened": 1,
  "delivery_rate": 0.85,
  "open_rate": 0.85
}
```

* **Optional Response Fields**: `total`, `sent`, `delivered`, `opened`, `delivery_rate`, `open_rate`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Get Notification
`GET` `/api/v1/notifications/{notification_id}`

**Path Parameters**:
* `notification_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "customer_id": null,
  "user_id": null,
  "type": "string",
  "title": "string",
  "body": "string",
  "channel": "string",
  "status": null,
  "priority": null,
  "campaign_id": null,
  "scheduled_at": null,
  "sent_at": null,
  "delivered_at": null,
  "opened_at": null,
  "clicked_at": null,
  "failed_at": null,
  "failure_reason": null,
  "retry_count": 1,
  "created_at": null
}
```

* **Required Response Fields**: `id`, `type`, `title`, `body`, `channel`
* **Optional Response Fields**: `customer_id`, `user_id`, `status`, `priority`, `campaign_id`, `scheduled_at`, `sent_at`, `delivered_at`, `opened_at`, `clicked_at`, `failed_at`, `failure_reason`, `retry_count`, `created_at`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Retry Notification
`POST` `/api/v1/notifications/{notification_id}/retry`

**Path Parameters**:
* `notification_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### List Users
`GET` `/api/v1/users`

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 
* `search` (string) - *(Optional)* 
* `sort_by` (string) - *(Optional)* 
* `sort_order` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "email": "string",
      "first_name": "string",
      "last_name": "string",
      "job_title": null,
      "department": null,
      "phone": null,
      "is_active": true,
      "is_verified": true,
      "last_login_at": null,
      "created_at": "2026-06-25T01:58:33Z",
      "updated_at": "2026-06-25T01:58:33Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Create User
`POST` `/api/v1/users`

**Request Body Example**:
```json
{
  "email": "user@example.com",
  "password": "string",
  "first_name": "string",
  "last_name": "string",
  "job_title": null,
  "department": null,
  "phone": null
}
```

* **Required Request Fields**: `email`, `password`, `first_name`, `last_name`
* **Optional Request Fields**: `job_title`, `department`, `phone`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "job_title": null,
  "department": null,
  "phone": null,
  "is_active": true,
  "is_verified": true,
  "last_login_at": null,
  "created_at": "2026-06-25T01:58:33Z",
  "updated_at": "2026-06-25T01:58:33Z"
}
```

* **Required Response Fields**: `id`, `organization_id`, `email`, `first_name`, `last_name`, `is_active`, `is_verified`, `created_at`, `updated_at`
* **Optional Response Fields**: `job_title`, `department`, `phone`, `last_login_at`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `409 Conflict`

---

### List Roles
`GET` `/api/v1/users/roles`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "name": "string",
    "description": null,
    "is_system": true,
    "permissions": [
      {}
    ]
  }
]
```


* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Create Role
`POST` `/api/v1/users/roles`

**Request Body Example**:
```json
{
  "name": "string",
  "description": null,
  "permissions": [
    {}
  ]
}
```

* **Required Request Fields**: `name`
* **Optional Request Fields**: `description`, `permissions`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "name": "string",
  "description": null,
  "is_system": true,
  "permissions": [
    {}
  ]
}
```

* **Required Response Fields**: `id`, `name`, `is_system`
* **Optional Response Fields**: `description`, `permissions`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `409 Conflict`

---

### Delete Role
`DELETE` `/api/v1/users/roles/{role_id}`

**Path Parameters**:
* `role_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show loading spinner on delete button, disable cancel button, and show confirmation modal block overlay.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Update Role
`PUT` `/api/v1/users/roles/{role_id}`

**Path Parameters**:
* `role_id` (string) - *(Required)* 

**Request Body Example**:
```json
{
  "name": "string",
  "description": null,
  "permissions": [
    {}
  ]
}
```

* **Required Request Fields**: `name`
* **Optional Request Fields**: `description`, `permissions`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "name": "string",
  "description": null,
  "is_system": true,
  "permissions": [
    {}
  ]
}
```

* **Required Response Fields**: `id`, `name`, `is_system`
* **Optional Response Fields**: `description`, `permissions`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Deactivate User
`DELETE` `/api/v1/users/{user_id}`

**Path Parameters**:
* `user_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show loading spinner on delete button, disable cancel button, and show confirmation modal block overlay.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get User
`GET` `/api/v1/users/{user_id}`

**Path Parameters**:
* `user_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "job_title": null,
  "department": null,
  "phone": null,
  "is_active": true,
  "is_verified": true,
  "last_login_at": null,
  "created_at": "2026-06-25T01:58:33Z",
  "updated_at": "2026-06-25T01:58:33Z"
}
```

* **Required Response Fields**: `id`, `organization_id`, `email`, `first_name`, `last_name`, `is_active`, `is_verified`, `created_at`, `updated_at`
* **Optional Response Fields**: `job_title`, `department`, `phone`, `last_login_at`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Update User
`PUT` `/api/v1/users/{user_id}`

**Path Parameters**:
* `user_id` (string) - *(Required)* 

**Request Body Example**:
```json
{
  "first_name": null,
  "last_name": null,
  "job_title": null,
  "department": null,
  "phone": null,
  "is_active": null
}
```

* **Optional Request Fields**: `first_name`, `last_name`, `job_title`, `department`, `phone`, `is_active`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "job_title": null,
  "department": null,
  "phone": null,
  "is_active": true,
  "is_verified": true,
  "last_login_at": null,
  "created_at": "2026-06-25T01:58:33Z",
  "updated_at": "2026-06-25T01:58:33Z"
}
```

* **Required Response Fields**: `id`, `organization_id`, `email`, `first_name`, `last_name`, `is_active`, `is_verified`, `created_at`, `updated_at`
* **Optional Response Fields**: `job_title`, `department`, `phone`, `last_login_at`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Assign User Roles
`PUT` `/api/v1/users/{user_id}/roles`

**Path Parameters**:
* `user_id` (string) - *(Required)* 

**Request Body Example**:
```json
[
  "string"
]
```


**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "job_title": null,
  "department": null,
  "phone": null,
  "is_active": true,
  "is_verified": true,
  "last_login_at": null,
  "created_at": "2026-06-25T01:58:33Z",
  "updated_at": "2026-06-25T01:58:33Z"
}
```

* **Required Response Fields**: `id`, `organization_id`, `email`, `first_name`, `last_name`, `is_active`, `is_verified`, `created_at`, `updated_at`
* **Optional Response Fields**: `job_title`, `department`, `phone`, `last_login_at`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Health
`GET` `/health`

* No Request Body.

* Response contains no payload (empty body).

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Readiness
`GET` `/ready`

* No Request Body.

* Response contains no payload (empty body).

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

## Customers

Contains endpoints driving customers functionalities, dashboards, data tables, and settings.

### List Customers
`GET` `/api/v1/customers`

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 
* `limit` (string) - *(Optional)* Alias for page_size
* `search` (string) - *(Optional)* 
* `email` (string) - *(Optional)* 
* `tags` (string) - *(Optional)* 
* `segment_ids` (string) - *(Optional)* 
* `sort_by` (string) - *(Optional)* 
* `sort_order` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "external_id": null,
      "email": null,
      "phone": null,
      "first_name": null,
      "last_name": null,
      "date_of_birth": null,
      "gender": null,
      "timezone": "string",
      "locale": "string",
      "location": null,
      "tags": [
        "string"
      ],
      "custom_attributes": {},
      "is_active": true,
      "consent_marketing": true,
      "consent_analytics": true,
      "consent_profiling": true,
      "source": null,
      "first_seen_at": null,
      "last_seen_at": null,
      "created_at": "2026-06-25T01:58:33Z",
      "updated_at": "2026-06-25T01:58:33Z",
      "name": null,
      "engagement_score": 0.85,
      "loyalty_score": 0.85,
      "churn_risk": "string",
      "ltv": 0.85,
      "last_activity": null,
      "segments": [
        "string"
      ],
      "twin_summary": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Create Customer
`POST` `/api/v1/customers`

**Request Body Example**:
```json
{
  "external_id": null,
  "email": null,
  "phone": null,
  "first_name": null,
  "last_name": null,
  "date_of_birth": null,
  "gender": null,
  "timezone": "string",
  "locale": "string",
  "location": null,
  "tags": [
    "string"
  ],
  "custom_attributes": {},
  "consent_marketing": true,
  "consent_analytics": true,
  "consent_profiling": true,
  "segment_ids": [
    "string"
  ]
}
```

* **Optional Request Fields**: `external_id`, `email`, `phone`, `first_name`, `last_name`, `date_of_birth`, `gender`, `timezone`, `locale`, `location`, `tags`, `custom_attributes`, `consent_marketing`, `consent_analytics`, `consent_profiling`, `segment_ids`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `409 Conflict`

---

### Batch Create Customers
`POST` `/api/v1/customers/batch`

**Request Body Example**:
```json
[
  {
    "external_id": null,
    "email": null,
    "phone": null,
    "first_name": null,
    "last_name": null,
    "date_of_birth": null,
    "gender": null,
    "timezone": "string",
    "locale": "string",
    "location": null,
    "tags": [
      "string"
    ],
    "custom_attributes": {},
    "consent_marketing": true,
    "consent_analytics": true,
    "consent_profiling": true,
    "segment_ids": [
      "string"
    ]
  }
]
```


**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `409 Conflict`

---

### New Customer
`GET` `/api/v1/customers/new`

* No Request Body.

* Response contains no payload (empty body).

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Search Customers
`GET` `/api/v1/customers/search`

**Query Parameters**:
* `q` (string) - *(Optional)* 
* `limit` (integer) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "external_id": null,
    "email": null,
    "phone": null,
    "first_name": null,
    "last_name": null,
    "date_of_birth": null,
    "gender": null,
    "timezone": "string",
    "locale": "string",
    "location": null,
    "tags": [
      "string"
    ],
    "custom_attributes": {},
    "is_active": true,
    "consent_marketing": true,
    "consent_analytics": true,
    "consent_profiling": true,
    "source": null,
    "first_seen_at": null,
    "last_seen_at": null,
    "created_at": "2026-06-25T01:58:33Z",
    "updated_at": "2026-06-25T01:58:33Z",
    "name": null,
    "engagement_score": 0.85,
    "loyalty_score": 0.85,
    "churn_risk": "string",
    "ltv": 0.85,
    "last_activity": null,
    "segments": [
      "string"
    ],
    "twin_summary": null
  }
]
```


* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Delete Customer
`DELETE` `/api/v1/customers/{customer_id}`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show loading spinner on delete button, disable cancel button, and show confirmation modal block overlay.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Customer
`GET` `/api/v1/customers/{customer_id}`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "external_id": null,
  "email": null,
  "phone": null,
  "first_name": null,
  "last_name": null,
  "date_of_birth": null,
  "gender": null,
  "timezone": "string",
  "locale": "string",
  "location": null,
  "tags": [
    "string"
  ],
  "custom_attributes": {},
  "is_active": true,
  "consent_marketing": true,
  "consent_analytics": true,
  "consent_profiling": true,
  "source": null,
  "first_seen_at": null,
  "last_seen_at": null,
  "created_at": "2026-06-25T01:58:33Z",
  "updated_at": "2026-06-25T01:58:33Z",
  "name": null,
  "engagement_score": 0.85,
  "loyalty_score": 0.85,
  "churn_risk": "string",
  "ltv": 0.85,
  "last_activity": null,
  "segments": [
    "string"
  ],
  "twin_summary": null
}
```

* **Required Response Fields**: `id`, `organization_id`, `timezone`, `locale`, `is_active`, `consent_marketing`, `consent_analytics`, `consent_profiling`, `created_at`, `updated_at`
* **Optional Response Fields**: `external_id`, `email`, `phone`, `first_name`, `last_name`, `date_of_birth`, `gender`, `location`, `tags`, `custom_attributes`, `source`, `first_seen_at`, `last_seen_at`, `name`, `engagement_score`, `loyalty_score`, `churn_risk`, `ltv`, `last_activity`, `segments`, `twin_summary`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Update Customer
`PUT` `/api/v1/customers/{customer_id}`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

**Request Body Example**:
```json
{
  "external_id": null,
  "email": null,
  "phone": null,
  "first_name": null,
  "last_name": null,
  "date_of_birth": null,
  "gender": null,
  "timezone": null,
  "locale": null,
  "location": null,
  "tags": null,
  "custom_attributes": null,
  "is_active": null,
  "consent_marketing": null,
  "consent_analytics": null,
  "consent_profiling": null,
  "segment_ids": null
}
```

* **Optional Request Fields**: `external_id`, `email`, `phone`, `first_name`, `last_name`, `date_of_birth`, `gender`, `timezone`, `locale`, `location`, `tags`, `custom_attributes`, `is_active`, `consent_marketing`, `consent_analytics`, `consent_profiling`, `segment_ids`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "external_id": null,
  "email": null,
  "phone": null,
  "first_name": null,
  "last_name": null,
  "date_of_birth": null,
  "gender": null,
  "timezone": "string",
  "locale": "string",
  "location": null,
  "tags": [
    "string"
  ],
  "custom_attributes": {},
  "is_active": true,
  "consent_marketing": true,
  "consent_analytics": true,
  "consent_profiling": true,
  "source": null,
  "first_seen_at": null,
  "last_seen_at": null,
  "created_at": "2026-06-25T01:58:33Z",
  "updated_at": "2026-06-25T01:58:33Z"
}
```

* **Required Response Fields**: `id`, `organization_id`, `timezone`, `locale`, `is_active`, `consent_marketing`, `consent_analytics`, `consent_profiling`, `created_at`, `updated_at`
* **Optional Response Fields**: `external_id`, `email`, `phone`, `first_name`, `last_name`, `date_of_birth`, `gender`, `location`, `tags`, `custom_attributes`, `source`, `first_seen_at`, `last_seen_at`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Get Customer Events
`GET` `/api/v1/customers/{customer_id}/events`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "customer_id": null,
      "session_id": null,
      "event_type": "string",
      "event_name": "string",
      "event_properties": {},
      "context": {},
      "channel": null,
      "source": null,
      "device_type": null,
      "device_os": null,
      "browser": null,
      "ip_address": null,
      "user_agent": null,
      "referrer": null,
      "url": null,
      "geolocation": null,
      "campaign_id": null,
      "value": null,
      "currency": null,
      "processed": true,
      "event_timestamp": null,
      "ingested_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Customer Interests
`GET` `/api/v1/customers/{customer_id}/interests`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "customer_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "category": "string",
    "subcategory": null,
    "interest_level": null,
    "affinity_score": null,
    "interaction_count": 1,
    "last_interaction_at": null,
    "is_active": true
  }
]
```


* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Merge Customers
`POST` `/api/v1/customers/{customer_id}/merge`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

**Request Body Example**:
```json
[
  "string"
]
```


**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`, `409 Conflict`

---

### Get Customer Preferences
`GET` `/api/v1/customers/{customer_id}/preferences`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "customer_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "channel_email": true,
  "channel_sms": true,
  "channel_push": true,
  "channel_in_app": true,
  "email_frequency": null,
  "sms_frequency": null,
  "push_frequency": null,
  "quiet_hours_start": null,
  "quiet_hours_end": null,
  "timezone": null,
  "preferred_categories": [
    "string"
  ],
  "preferred_brands": [
    "string"
  ],
  "excluded_categories": [
    "string"
  ],
  "max_communications_per_day": null,
  "do_not_disturb": true
}
```

* **Required Response Fields**: `id`, `customer_id`
* **Optional Response Fields**: `channel_email`, `channel_sms`, `channel_push`, `channel_in_app`, `email_frequency`, `sms_frequency`, `push_frequency`, `quiet_hours_start`, `quiet_hours_end`, `timezone`, `preferred_categories`, `preferred_brands`, `excluded_categories`, `max_communications_per_day`, `do_not_disturb`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Update Customer Preferences
`PUT` `/api/v1/customers/{customer_id}/preferences`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

**Request Body Example**:
```json
{}
```


**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "customer_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "channel_email": true,
  "channel_sms": true,
  "channel_push": true,
  "channel_in_app": true,
  "email_frequency": null,
  "sms_frequency": null,
  "push_frequency": null,
  "quiet_hours_start": null,
  "quiet_hours_end": null,
  "timezone": null,
  "preferred_categories": [
    "string"
  ],
  "preferred_brands": [
    "string"
  ],
  "excluded_categories": [
    "string"
  ],
  "max_communications_per_day": null,
  "do_not_disturb": true
}
```

* **Required Response Fields**: `id`, `customer_id`
* **Optional Response Fields**: `channel_email`, `channel_sms`, `channel_push`, `channel_in_app`, `email_frequency`, `sms_frequency`, `push_frequency`, `quiet_hours_start`, `quiet_hours_end`, `timezone`, `preferred_categories`, `preferred_brands`, `excluded_categories`, `max_communications_per_day`, `do_not_disturb`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Get Customer Profile
`GET` `/api/v1/customers/{customer_id}/profile`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "customer_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "title": null,
  "company": null,
  "industry": null,
  "annual_revenue": null,
  "employee_count": null,
  "website": null,
  "linkedin_url": null,
  "twitter_handle": null,
  "bio": null,
  "avatar_url": null,
  "preferred_language": null,
  "communication_style": null,
  "personality_traits": null,
  "psychographic_segment": null,
  "enrichment_status": null,
  "last_enriched_at": null
}
```

* **Required Response Fields**: `id`, `customer_id`
* **Optional Response Fields**: `title`, `company`, `industry`, `annual_revenue`, `employee_count`, `website`, `linkedin_url`, `twitter_handle`, `bio`, `avatar_url`, `preferred_language`, `communication_style`, `personality_traits`, `psychographic_segment`, `enrichment_status`, `last_enriched_at`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Customer Segments
`GET` `/api/v1/customers/{customer_id}/segments`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "name": "string",
    "description": null,
    "source": null,
    "rules": null,
    "customer_count": 1,
    "is_active": true,
    "is_dynamic": true,
    "refresh_interval_minutes": null,
    "last_refreshed_at": null
  }
]
```


* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### List Events
`GET` `/api/v1/events`

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 
* `customer_id` (string) - *(Optional)* 
* `event_type` (string) - *(Optional)* 
* `source` (string) - *(Optional)* 
* `start_date` (string) - *(Optional)* 
* `end_date` (string) - *(Optional)* 
* `search` (string) - *(Optional)* 
* `sort_by` (string) - *(Optional)* 
* `sort_order` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "customer_id": null,
      "session_id": null,
      "event_type": "string",
      "event_name": "string",
      "event_properties": {},
      "context": {},
      "channel": null,
      "source": null,
      "device_type": null,
      "device_os": null,
      "browser": null,
      "ip_address": null,
      "user_agent": null,
      "referrer": null,
      "url": null,
      "geolocation": null,
      "campaign_id": null,
      "value": null,
      "currency": null,
      "processed": true,
      "event_timestamp": null,
      "ingested_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Create Event
`POST` `/api/v1/events`

**Request Body Example**:
```json
{
  "customer_id": null,
  "event_type": "string",
  "event_name": "string",
  "event_properties": {},
  "context": {},
  "channel": null,
  "source": null,
  "device_type": null,
  "device_os": null,
  "browser": null,
  "ip_address": null,
  "user_agent": null,
  "referrer": null,
  "url": null,
  "geolocation": null,
  "campaign_id": null,
  "value": null,
  "currency": null,
  "event_timestamp": null
}
```

* **Required Request Fields**: `event_type`, `event_name`
* **Optional Request Fields**: `customer_id`, `event_properties`, `context`, `channel`, `source`, `device_type`, `device_os`, `browser`, `ip_address`, `user_agent`, `referrer`, `url`, `geolocation`, `campaign_id`, `value`, `currency`, `event_timestamp`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Batch Ingest Events
`POST` `/api/v1/events/batch`

**Request Body Example**:
```json
{
  "events": [
    {
      "customer_id": null,
      "event_type": "string",
      "event_name": "string",
      "event_properties": {},
      "context": {},
      "channel": null,
      "source": null,
      "device_type": null,
      "device_os": null,
      "browser": null,
      "ip_address": null,
      "user_agent": null,
      "referrer": null,
      "url": null,
      "geolocation": null,
      "campaign_id": null,
      "value": null,
      "currency": null,
      "event_timestamp": null
    }
  ]
}
```

* **Required Request Fields**: `events`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Get Event Summary
`GET` `/api/v1/events/summary`

**Query Parameters**:
* `start_date` (string) - *(Optional)* 
* `end_date` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "event_type": "string",
    "count": 1
  }
]
```


* **Loading State Handling**: Display circular progress indicator or shimmer header cards.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### List Event Types
`GET` `/api/v1/events/types`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "event_type": "string",
    "count": 1
  }
]
```


* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Get Event
`GET` `/api/v1/events/{event_id}`

**Path Parameters**:
* `event_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "customer_id": null,
  "session_id": null,
  "event_type": "string",
  "event_name": "string",
  "event_properties": {},
  "context": {},
  "channel": null,
  "source": null,
  "device_type": null,
  "device_os": null,
  "browser": null,
  "ip_address": null,
  "user_agent": null,
  "referrer": null,
  "url": null,
  "geolocation": null,
  "campaign_id": null,
  "value": null,
  "currency": null,
  "processed": true,
  "event_timestamp": null,
  "ingested_at": null
}
```

* **Required Response Fields**: `id`, `organization_id`, `event_type`, `event_name`
* **Optional Response Fields**: `customer_id`, `session_id`, `event_properties`, `context`, `channel`, `source`, `device_type`, `device_os`, `browser`, `ip_address`, `user_agent`, `referrer`, `url`, `geolocation`, `campaign_id`, `value`, `currency`, `processed`, `event_timestamp`, `ingested_at`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### List Segments
`GET` `/api/v1/segments`

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 
* `search` (string) - *(Optional)* 
* `sort_by` (string) - *(Optional)* 
* `sort_order` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "name": "string",
      "description": null,
      "source": null,
      "rules": null,
      "customer_count": 1,
      "is_active": true,
      "is_dynamic": true,
      "refresh_interval_minutes": null,
      "last_refreshed_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Create Segment
`POST` `/api/v1/segments`

**Request Body Example**:
```json
{}
```


**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Compute All Segments
`POST` `/api/v1/segments/compute`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show global page blocker or dynamic progress bar toast. Disable target trigger button and display inline spinner.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Delete Segment
`DELETE` `/api/v1/segments/{segment_id}`

**Path Parameters**:
* `segment_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show loading spinner on delete button, disable cancel button, and show confirmation modal block overlay.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Segment
`GET` `/api/v1/segments/{segment_id}`

**Path Parameters**:
* `segment_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "name": "string",
  "description": null,
  "source": null,
  "rules": null,
  "customer_count": 1,
  "is_active": true,
  "is_dynamic": true,
  "refresh_interval_minutes": null,
  "last_refreshed_at": null
}
```

* **Required Response Fields**: `id`, `name`
* **Optional Response Fields**: `description`, `source`, `rules`, `customer_count`, `is_active`, `is_dynamic`, `refresh_interval_minutes`, `last_refreshed_at`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Update Segment
`PUT` `/api/v1/segments/{segment_id}`

**Path Parameters**:
* `segment_id` (string) - *(Required)* 

**Request Body Example**:
```json
{}
```


**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "name": "string",
  "description": null,
  "source": null,
  "rules": null,
  "customer_count": 1,
  "is_active": true,
  "is_dynamic": true,
  "refresh_interval_minutes": null,
  "last_refreshed_at": null
}
```

* **Required Response Fields**: `id`, `name`
* **Optional Response Fields**: `description`, `source`, `rules`, `customer_count`, `is_active`, `is_dynamic`, `refresh_interval_minutes`, `last_refreshed_at`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Get Segment Customers
`GET` `/api/v1/segments/{segment_id}/customers`

**Path Parameters**:
* `segment_id` (string) - *(Required)* 

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "external_id": null,
      "email": null,
      "phone": null,
      "first_name": null,
      "last_name": null,
      "date_of_birth": null,
      "gender": null,
      "timezone": "string",
      "locale": "string",
      "location": null,
      "tags": [
        "string"
      ],
      "custom_attributes": {},
      "is_active": true,
      "consent_marketing": true,
      "consent_analytics": true,
      "consent_profiling": true,
      "source": null,
      "first_seen_at": null,
      "last_seen_at": null,
      "created_at": "2026-06-25T01:58:33Z",
      "updated_at": "2026-06-25T01:58:33Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Create Lookalike Segment
`POST` `/api/v1/segments/{segment_id}/lookalike`

**Path Parameters**:
* `segment_id` (string) - *(Required)* 

**Request Body Example**:
```json
{}
```


**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Refresh Segment
`POST` `/api/v1/segments/{segment_id}/refresh`

**Path Parameters**:
* `segment_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show global page blocker or dynamic progress bar toast. Disable target trigger button and display inline spinner.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

## Twins

Contains endpoints driving twins functionalities, dashboards, data tables, and settings.

### Get Twin Summary
`GET` `/api/v1/twins/summary`

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "total_twins": 1,
  "avg_engagement": 0.85,
  "avg_loyalty": 0.85,
  "avg_sentiment": 0.85,
  "churn_risk_distribution": {},
  "top_interests": [
    {}
  ]
}
```

* **Optional Response Fields**: `total_twins`, `avg_engagement`, `avg_loyalty`, `avg_sentiment`, `churn_risk_distribution`, `top_interests`

* **Loading State Handling**: Display circular progress indicator or shimmer header cards.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Get Customer Twin
`GET` `/api/v1/twins/{customer_id}`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

* No Request Body.

* Response contains no payload (empty body).

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Twin History
`GET` `/api/v1/twins/{customer_id}/history`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

**Query Parameters**:
* `limit` (integer) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "twin_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "snapshot_type": "string",
    "snapshot_data": {},
    "scores": {},
    "valid_from": "2026-06-25T01:58:33Z",
    "valid_until": null,
    "created_at": null,
    "updated_at": null
  }
]
```


* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Rebuild Twin
`POST` `/api/v1/twins/{customer_id}/rebuild`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show global page blocker or dynamic progress bar toast. Disable target trigger button and display inline spinner.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

## Predictions

Contains endpoints driving predictions functionalities, dashboards, data tables, and settings.

### List Recommendations
`GET` `/api/v1/recommendations`

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 
* `customer_id` (string) - *(Optional)* 
* `recommendation_type` (string) - *(Optional)* 
* `status` (string) - *(Optional)* 
* `sort_by` (string) - *(Optional)* 
* `sort_order` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "customer_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "type": "string",
      "title": "string",
      "description": null,
      "score": null,
      "rank": null,
      "category": null,
      "metadata": {},
      "is_actionable": true,
      "is_applied": true,
      "applied_at": null,
      "source": null,
      "expires_at": null,
      "created_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Submit Recommendation Feedback
`POST` `/api/v1/recommendations/feedback`

**Request Body Example**:
```json
{
  "recommendation_id": null,
  "feedback_type": "string"
}
```

* **Required Request Fields**: `recommendation_id`, `feedback_type`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Get Personalized Recommendations
`GET` `/api/v1/recommendations/{customer_id}/personalized`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

**Query Parameters**:
* `limit` (integer) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "customer_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "type": "string",
    "title": "string",
    "description": null,
    "score": null,
    "rank": null,
    "category": null,
    "metadata": {},
    "is_actionable": true,
    "is_applied": true,
    "applied_at": null,
    "source": null,
    "expires_at": null,
    "created_at": null
  }
]
```


* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Refresh Customer Recommendations
`POST` `/api/v1/recommendations/{customer_id}/refresh`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show global page blocker or dynamic progress bar toast. Disable target trigger button and display inline spinner.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Get Predictions
`GET` `/api/v1/twins/{customer_id}/predictions`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 

**Query Parameters**:
* `prediction_type` (string) - *(Optional)* 
* `limit` (integer) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "customer_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "prediction_type": "string",
    "prediction_value": 0.85,
    "prediction_probability": null,
    "prediction_label": null,
    "prediction_explanation": {},
    "feature_importance": {},
    "confidence_score": null,
    "model_version": "string",
    "model_name": "string",
    "input_features": {},
    "valid_until": null,
    "is_active": true,
    "created_at": null,
    "timestamp": null,
    "confidence": null,
    "value": null
  }
]
```


* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Latest Prediction
`GET` `/api/v1/twins/{customer_id}/predictions/{prediction_type}`

**Path Parameters**:
* `customer_id` (string) - *(Required)* 
* `prediction_type` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "customer_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "prediction_type": "string",
  "prediction_value": 0.85,
  "prediction_probability": null,
  "prediction_label": null,
  "prediction_explanation": {},
  "feature_importance": {},
  "confidence_score": null,
  "model_version": "string",
  "model_name": "string",
  "input_features": {},
  "valid_until": null,
  "is_active": true,
  "created_at": null,
  "timestamp": null,
  "confidence": null,
  "value": null
}
```

* **Required Response Fields**: `id`, `customer_id`, `organization_id`, `prediction_type`, `prediction_value`, `model_version`, `model_name`, `timestamp`, `confidence`, `value`
* **Optional Response Fields**: `prediction_probability`, `prediction_label`, `prediction_explanation`, `feature_importance`, `confidence_score`, `input_features`, `valid_until`, `is_active`, `created_at`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

## Simulations

Contains endpoints driving simulations functionalities, dashboards, data tables, and settings.

### List Simulations
`GET` `/api/v1/simulations`

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 
* `status` (string) - *(Optional)* 
* `search` (string) - *(Optional)* 
* `sort_by` (string) - *(Optional)* 
* `sort_order` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "name": "string",
      "config": {
        "iterations": 1,
        "time_horizon": 1,
        "confidence_level": 0.85,
        "segment_ids": [
          "string"
        ],
        "parameters": {}
      },
      "status": null,
      "results": null,
      "forecast": null,
      "created_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Create Simulation
`POST` `/api/v1/simulations`

**Request Body Example**:
```json
{
  "name": "string",
  "description": null,
  "type": "string",
  "campaign_id": null,
  "configuration": {},
  "parameters": {},
  "agent_configuration": {},
  "monte_carlo_iterations": 1,
  "confidence_level": 0.85,
  "time_horizon_days": 1,
  "iterations": null,
  "time_horizon": null,
  "segment_ids": [
    "string"
  ],
  "sample_size": 1,
  "include_control": true,
  "expected_outputs": [
    "string"
  ]
}
```

* **Required Request Fields**: `name`
* **Optional Request Fields**: `description`, `type`, `campaign_id`, `configuration`, `parameters`, `agent_configuration`, `monte_carlo_iterations`, `confidence_level`, `time_horizon_days`, `iterations`, `time_horizon`, `segment_ids`, `sample_size`, `include_control`, `expected_outputs`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "name": "string",
  "config": {
    "iterations": 1,
    "time_horizon": 1,
    "confidence_level": 0.85,
    "segment_ids": [
      "string"
    ],
    "parameters": {}
  },
  "status": null,
  "results": null,
  "forecast": null,
  "created_at": null
}
```

* **Required Response Fields**: `id`, `name`, `config`
* **Optional Response Fields**: `status`, `results`, `forecast`, `created_at`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `409 Conflict`

---

### Delete Simulation
`DELETE` `/api/v1/simulations/{simulation_id}`

**Path Parameters**:
* `simulation_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show loading spinner on delete button, disable cancel button, and show confirmation modal block overlay.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Simulation
`GET` `/api/v1/simulations/{simulation_id}`

**Path Parameters**:
* `simulation_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "name": "string",
  "config": {
    "iterations": 1,
    "time_horizon": 1,
    "confidence_level": 0.85,
    "segment_ids": [
      "string"
    ],
    "parameters": {}
  },
  "status": null,
  "results": null,
  "forecast": null,
  "created_at": null
}
```

* **Required Response Fields**: `id`, `name`, `config`
* **Optional Response Fields**: `status`, `results`, `forecast`, `created_at`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Update Simulation
`PUT` `/api/v1/simulations/{simulation_id}`

**Path Parameters**:
* `simulation_id` (string) - *(Required)* 

**Request Body Example**:
```json
{
  "name": null,
  "description": null,
  "type": null,
  "campaign_id": null,
  "configuration": null,
  "parameters": null,
  "agent_configuration": null,
  "monte_carlo_iterations": null,
  "confidence_level": null,
  "time_horizon_days": null,
  "segment_ids": null,
  "sample_size": null,
  "include_control": null,
  "expected_outputs": null
}
```

* **Optional Request Fields**: `name`, `description`, `type`, `campaign_id`, `configuration`, `parameters`, `agent_configuration`, `monte_carlo_iterations`, `confidence_level`, `time_horizon_days`, `segment_ids`, `sample_size`, `include_control`, `expected_outputs`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "name": "string",
  "config": {
    "iterations": 1,
    "time_horizon": 1,
    "confidence_level": 0.85,
    "segment_ids": [
      "string"
    ],
    "parameters": {}
  },
  "status": null,
  "results": null,
  "forecast": null,
  "created_at": null
}
```

* **Required Response Fields**: `id`, `name`, `config`
* **Optional Response Fields**: `status`, `results`, `forecast`, `created_at`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Get Simulation Forecast
`GET` `/api/v1/simulations/{simulation_id}/forecast`

**Path Parameters**:
* `simulation_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "expected_revenue": null,
  "expected_conversions": null,
  "expected_open_rate": null,
  "expected_click_rate": null,
  "revenue_confidence_interval": [
    0.85
  ],
  "conversion_confidence_interval": [
    0.85
  ],
  "scenarios": {},
  "sensitivity": [
    {}
  ],
  "risk_assessment": {}
}
```

* **Optional Response Fields**: `expected_revenue`, `expected_conversions`, `expected_open_rate`, `expected_click_rate`, `revenue_confidence_interval`, `conversion_confidence_interval`, `scenarios`, `sensitivity`, `risk_assessment`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Simulation Progress
`GET` `/api/v1/simulations/{simulation_id}/progress`

**Path Parameters**:
* `simulation_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "progress": 0.85,
  "status": "active"
}
```

* **Required Response Fields**: `status`
* **Optional Response Fields**: `progress`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Simulation Results
`GET` `/api/v1/simulations/{simulation_id}/results`

**Path Parameters**:
* `simulation_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "simulation_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "run_id": null,
  "aggregated_metrics": {},
  "customer_projections": {},
  "segment_projections": {},
  "campaign_impact": {},
  "confidence_intervals": {},
  "monte_carlo_distribution": {},
  "expected_outcomes": {},
  "risk_assessment": {},
  "recommendations": [
    "string"
  ]
}
```

* **Required Response Fields**: `id`, `simulation_id`
* **Optional Response Fields**: `run_id`, `aggregated_metrics`, `customer_projections`, `segment_projections`, `campaign_impact`, `confidence_intervals`, `monte_carlo_distribution`, `expected_outcomes`, `risk_assessment`, `recommendations`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Run Simulation
`POST` `/api/v1/simulations/{simulation_id}/run`

**Path Parameters**:
* `simulation_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show global page blocker or dynamic progress bar toast. Disable target trigger button and display inline spinner.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`, `409 Conflict`

---

### Get Simulation Runs
`GET` `/api/v1/simulations/{simulation_id}/runs`

**Path Parameters**:
* `simulation_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "simulation_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "run_number": 1,
    "status": null,
    "seed": null,
    "agents_count": null,
    "iterations_executed": null,
    "runtime_seconds": null,
    "cpu_usage": null,
    "memory_usage_bytes": null,
    "error_message": null,
    "logs": null,
    "started_at": null,
    "completed_at": null
  }
]
```


* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Simulation Status
`GET` `/api/v1/simulations/{simulation_id}/status`

**Path Parameters**:
* `simulation_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "status": "active",
  "progress": 0.85,
  "started_at": null,
  "completed_at": null
}
```

* **Required Response Fields**: `id`, `status`
* **Optional Response Fields**: `progress`, `started_at`, `completed_at`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

## Analytics

Contains endpoints driving analytics functionalities, dashboards, data tables, and settings.

### Compare Campaign Performance
`GET` `/api/v1/analytics/campaigns`

**Query Parameters**:
* `campaign_ids` (string) - *(Optional)* 
* `start_date` (string) - *(Optional)* 
* `end_date` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
[
  {
    "campaign_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
    "campaign_name": "string",
    "status": null,
    "total_targeted": 1,
    "total_delivered": 1,
    "total_opened": 1,
    "total_clicked": 1,
    "total_converted": 1,
    "total_revenue": 0.85,
    "open_rate": null,
    "click_rate": null,
    "conversion_rate": null,
    "roi": null
  }
]
```


* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Get Churn Analytics
`GET` `/api/v1/analytics/churn`

**Query Parameters**:
* `granularity` (string) - *(Optional)* 
* `start_date` (string) - *(Optional)* 
* `end_date` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "churn_rate": null,
  "churned_customers": 1,
  "at_risk_customers": 1,
  "churn_by_segment": [
    {}
  ],
  "churn_reasons": [
    {}
  ],
  "retention_rate": null,
  "period": "string"
}
```

* **Optional Response Fields**: `churn_rate`, `churned_customers`, `at_risk_customers`, `churn_by_segment`, `churn_reasons`, `retention_rate`, `period`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Get Engagement Trends
`GET` `/api/v1/analytics/engagement`

**Query Parameters**:
* `granularity` (string) - *(Optional)* 
* `start_date` (string) - *(Optional)* 
* `end_date` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "overall_score": null,
  "trend": [
    {}
  ],
  "by_channel": {},
  "by_segment": {},
  "period": "string"
}
```

* **Optional Response Fields**: `overall_score`, `trend`, `by_channel`, `by_segment`, `period`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Export Analytics
`GET` `/api/v1/analytics/export`

**Query Parameters**:
* `report_type` (string) - *(Optional)* 
* `format` (string) - *(Optional)* 
* `start_date` (string) - *(Optional)* 
* `end_date` (string) - *(Optional)* 

* No Request Body.

* Response contains no payload (empty body).

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Run Analytics Query
`POST` `/api/v1/analytics/query`

**Request Body Example**:
```json
{
  "metric": "string",
  "dimension": "string",
  "segment_id": null,
  "date_from": "2026-06-25T01:58:33Z",
  "date_to": "2026-06-25T01:58:33Z",
  "granularity": "string",
  "filters": {},
  "dimensions": null
}
```

* **Required Request Fields**: `metric`, `dimension`, `date_from`, `date_to`
* **Optional Request Fields**: `segment_id`, `granularity`, `filters`, `dimensions`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "metric": "string",
  "dimension": "string",
  "granularity": "string",
  "data": [
    {}
  ],
  "summary": {},
  "total": 1
}
```

* **Required Response Fields**: `metric`, `dimension`, `granularity`
* **Optional Response Fields**: `data`, `summary`, `total`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`

---

### Get Revenue Analytics
`GET` `/api/v1/analytics/revenue`

**Query Parameters**:
* `granularity` (string) - *(Optional)* 
* `start_date` (string) - *(Optional)* 
* `end_date` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "total_revenue": 0.85,
  "recurring_revenue": 0.85,
  "average_order_value": null,
  "revenue_by_channel": {},
  "revenue_trend": [
    {}
  ],
  "period": "string",
  "currency": "string"
}
```

* **Optional Response Fields**: `total_revenue`, `recurring_revenue`, `average_order_value`, `revenue_by_channel`, `revenue_trend`, `period`, `currency`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Get Segment Analytics
`GET` `/api/v1/analytics/segments/{segment_id}`

**Path Parameters**:
* `segment_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "segment_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "segment_name": "string",
  "customer_count": 1,
  "avg_engagement": null,
  "avg_loyalty": null,
  "total_ltv": 0.85,
  "churn_rate": null,
  "growth_rate": null,
  "top_interests": [
    {}
  ]
}
```

* **Required Response Fields**: `segment_id`, `segment_name`
* **Optional Response Fields**: `customer_count`, `avg_engagement`, `avg_loyalty`, `total_ltv`, `churn_rate`, `growth_rate`, `top_interests`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

## Campaigns

Contains endpoints driving campaigns functionalities, dashboards, data tables, and settings.

### List Campaigns
`GET` `/api/v1/campaigns`

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 
* `status` (string) - *(Optional)* 
* `search` (string) - *(Optional)* 
* `sort_by` (string) - *(Optional)* 
* `sort_order` (string) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "name": "string",
      "description": null,
      "type": "string",
      "goal": null,
      "status": null,
      "channel": "string",
      "segments": null,
      "target_customers": [
        "string"
      ],
      "exclude_customers": [
        "string"
      ],
      "content": {},
      "schedule": {},
      "budget": null,
      "expected_reach": null,
      "expected_conversion_rate": null,
      "ab_test_config": {},
      "frequency_cap": 1,
      "frequency_cap_period": "string",
      "start_at": null,
      "end_at": null,
      "executed_at": null,
      "completed_at": null,
      "created_by": null,
      "created_at": null,
      "updated_at": null,
      "result_summary": null,
      "metrics": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display table skeleton rows (shimmer layout). Disable search & pagination controls.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`

---

### Create Campaign
`POST` `/api/v1/campaigns`

**Request Body Example**:
```json
{
  "name": "string",
  "description": null,
  "type": "string",
  "goal": null,
  "channel": "string",
  "segments": [
    "string"
  ],
  "target_customers": [
    "string"
  ],
  "exclude_customers": [
    "string"
  ],
  "content": {},
  "schedule": {},
  "budget": null,
  "expected_reach": null,
  "expected_conversion_rate": null,
  "ab_test_config": {},
  "frequency_cap": 1,
  "frequency_cap_period": "string",
  "start_at": null,
  "end_at": null
}
```

* **Required Request Fields**: `name`, `type`, `channel`
* **Optional Request Fields**: `description`, `goal`, `segments`, `target_customers`, `exclude_customers`, `content`, `schedule`, `budget`, `expected_reach`, `expected_conversion_rate`, `ab_test_config`, `frequency_cap`, `frequency_cap_period`, `start_at`, `end_at`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `409 Conflict`

---

### Delete Campaign
`DELETE` `/api/v1/campaigns/{campaign_id}`

**Path Parameters**:
* `campaign_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show loading spinner on delete button, disable cancel button, and show confirmation modal block overlay.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Get Campaign
`GET` `/api/v1/campaigns/{campaign_id}`

**Path Parameters**:
* `campaign_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "name": "string",
  "description": null,
  "type": "string",
  "goal": null,
  "status": null,
  "channel": "string",
  "segments": null,
  "target_customers": [
    "string"
  ],
  "exclude_customers": [
    "string"
  ],
  "content": {},
  "schedule": {},
  "budget": null,
  "expected_reach": null,
  "expected_conversion_rate": null,
  "ab_test_config": {},
  "frequency_cap": 1,
  "frequency_cap_period": "string",
  "start_at": null,
  "end_at": null,
  "executed_at": null,
  "completed_at": null,
  "created_by": null,
  "created_at": null,
  "updated_at": null
}
```

* **Required Response Fields**: `id`, `organization_id`, `name`, `type`, `channel`
* **Optional Response Fields**: `description`, `goal`, `status`, `segments`, `target_customers`, `exclude_customers`, `content`, `schedule`, `budget`, `expected_reach`, `expected_conversion_rate`, `ab_test_config`, `frequency_cap`, `frequency_cap_period`, `start_at`, `end_at`, `executed_at`, `completed_at`, `created_by`, `created_at`, `updated_at`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Update Campaign
`PUT` `/api/v1/campaigns/{campaign_id}`

**Path Parameters**:
* `campaign_id` (string) - *(Required)* 

**Request Body Example**:
```json
{
  "name": null,
  "description": null,
  "type": null,
  "goal": null,
  "channel": null,
  "segments": null,
  "target_customers": null,
  "exclude_customers": null,
  "content": null,
  "schedule": null,
  "budget": null,
  "expected_reach": null,
  "expected_conversion_rate": null,
  "ab_test_config": null,
  "frequency_cap": null,
  "frequency_cap_period": null,
  "start_at": null,
  "end_at": null
}
```

* **Optional Request Fields**: `name`, `description`, `type`, `goal`, `channel`, `segments`, `target_customers`, `exclude_customers`, `content`, `schedule`, `budget`, `expected_reach`, `expected_conversion_rate`, `ab_test_config`, `frequency_cap`, `frequency_cap_period`, `start_at`, `end_at`

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "organization_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "name": "string",
  "description": null,
  "type": "string",
  "goal": null,
  "status": null,
  "channel": "string",
  "segments": null,
  "target_customers": [
    "string"
  ],
  "exclude_customers": [
    "string"
  ],
  "content": {},
  "schedule": {},
  "budget": null,
  "expected_reach": null,
  "expected_conversion_rate": null,
  "ab_test_config": {},
  "frequency_cap": 1,
  "frequency_cap_period": "string",
  "start_at": null,
  "end_at": null,
  "executed_at": null,
  "completed_at": null,
  "created_by": null,
  "created_at": null,
  "updated_at": null
}
```

* **Required Response Fields**: `id`, `organization_id`, `name`, `type`, `channel`
* **Optional Response Fields**: `description`, `goal`, `status`, `segments`, `target_customers`, `exclude_customers`, `content`, `schedule`, `budget`, `expected_reach`, `expected_conversion_rate`, `ab_test_config`, `frequency_cap`, `frequency_cap_period`, `start_at`, `end_at`, `executed_at`, `completed_at`, `created_by`, `created_at`, `updated_at`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`

---

### Cancel Campaign
`POST` `/api/v1/campaigns/{campaign_id}/cancel`

**Path Parameters**:
* `campaign_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`, `409 Conflict`

---

### Launch Campaign
`POST` `/api/v1/campaigns/{campaign_id}/launch`

**Path Parameters**:
* `campaign_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`, `409 Conflict`

---

### Pause Campaign
`POST` `/api/v1/campaigns/{campaign_id}/pause`

**Path Parameters**:
* `campaign_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Disable form inputs, show inline loading spinner on the submit/action button, and prevent multiple submissions.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`, `409 Conflict`

---

### Get Campaign Results
`GET` `/api/v1/campaigns/{campaign_id}/results`

**Path Parameters**:
* `campaign_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "campaign_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
  "total_targeted": 1,
  "total_delivered": 1,
  "total_opened": 1,
  "total_clicked": 1,
  "total_converted": 1,
  "total_revenue": 0.85,
  "total_cost": 0.85,
  "open_rate": null,
  "click_rate": null,
  "conversion_rate": null,
  "bounce_rate": null,
  "unsubscribe_rate": null,
  "roi": null,
  "engagement_distribution": {},
  "channel_performance": {},
  "segment_performance": {},
  "hourly_breakdown": [
    {}
  ],
  "daily_breakdown": [
    {}
  ],
  "ab_test_results": {},
  "control_group_results": {},
  "treatment_group_results": {},
  "computed_at": null
}
```

* **Required Response Fields**: `id`, `campaign_id`
* **Optional Response Fields**: `total_targeted`, `total_delivered`, `total_opened`, `total_clicked`, `total_converted`, `total_revenue`, `total_cost`, `open_rate`, `click_rate`, `conversion_rate`, `bounce_rate`, `unsubscribe_rate`, `roi`, `engagement_distribution`, `channel_performance`, `segment_performance`, `hourly_breakdown`, `daily_breakdown`, `ab_test_results`, `control_group_results`, `treatment_group_results`, `computed_at`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---

### Simulate Campaign
`POST` `/api/v1/campaigns/{campaign_id}/simulate`

**Path Parameters**:
* `campaign_id` (string) - *(Required)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "success": true,
  "data": null,
  "error": null,
  "message": null,
  "request_id": null
}
```

* **Optional Response Fields**: `success`, `data`, `error`, `message`, `request_id`

* **Loading State Handling**: Show global page blocker or dynamic progress bar toast. Disable target trigger button and display inline spinner.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `422 Validation Error`, `404 Not Found`, `409 Conflict`

---

### Get Campaign Targets
`GET` `/api/v1/campaigns/{campaign_id}/targets`

**Path Parameters**:
* `campaign_id` (string) - *(Required)* 

**Query Parameters**:
* `page` (integer) - *(Optional)* 
* `page_size` (integer) - *(Optional)* 

* No Request Body.

**Response Body Example (200 OK / 201 Created)**:
```json
{
  "data": [
    {
      "id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "customer_id": "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
      "treatment": null,
      "score": null,
      "priority": null,
      "status": null,
      "delivered_at": null,
      "opened_at": null,
      "clicked_at": null,
      "converted_at": null,
      "revenue": null,
      "engagement_score": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 1,
  "limit": 1,
  "total_pages": 1,
  "has_next": true,
  "has_prev": true
}
```

* **Required Response Fields**: `data`, `total`, `page`, `page_size`, `limit`, `total_pages`, `has_next`, `has_prev`

* **Loading State Handling**: Display full-page skeleton details form or loading spinner. Disable primary action buttons.
* **Expected Error States**: `401 Unauthorized`, `500 Internal Server Error`, `404 Not Found`

---
