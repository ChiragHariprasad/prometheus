from fastapi import APIRouter

from app.api.v1 import (
    auth, users, customers, twins, events,
    campaigns, simulations, recommendations,
    notifications, analytics, segments, admin,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(twins.router, prefix="/twins", tags=["Digital Twins"])
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(simulations.router, prefix="/simulations", tags=["Simulations"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(segments.router, prefix="/segments", tags=["Segments"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])
