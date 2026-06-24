import traceback
import sys
from fastapi.testclient import TestClient
from app.main import app

with open("debugger_output.txt", "w") as f:
    endpoints = [
        ("/api/v1/customers", "GET"),
        ("/api/v1/customers?limit=10", "GET"),
        ("/api/v1/customers/search", "GET"),
        ("/api/v1/notifications/stats", "GET"),
        ("/api/v1/events/summary", "GET"),
        ("/api/v1/analytics/export", "GET"),
    ]

    with TestClient(app) as client:
        for path, method in endpoints:
            f.write(f"\n--- Testing {method} {path} ---\n")
            try:
                params = {}
                if "search" in path:
                    params = {"q": "test"}
                
                if method == "GET":
                    response = client.get(path, params=params)
                f.write(f"Status Code: {response.status_code}\n")
                f.write(f"Response JSON: {response.json()}\n")
            except Exception as e:
                f.write(f"Exception raised:\n")
                f.write(traceback.format_exc())
                f.write("\n")
