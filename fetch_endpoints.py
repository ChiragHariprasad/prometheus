#!/usr/bin/env python3
"""
PROMETHEUS Backend Validation Framework
This is the official benchmark framework.
The framework must never be weakened to accommodate backend bugs.
"""

import json
import os
import sys
import time
import uuid
import statistics
import concurrent.futures
from pathlib import Path
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

BASE_URL = "http://localhost:8004"
OUT_DIR = Path(__file__).resolve().parent / "prometheus_validation_reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc).isoformat()

class PrometheusValidator:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.metrics = []
        self.openapi_spec = None
        self.errors = []
        self.warnings = []
        self.scorecard = {
            "API Reliability": 20,
            "Twin Engine": 20,
            "Prediction Engine": 15,
            "Simulation Engine": 25,
            "Performance": 10,
            "Data Quality": 10
        }
        self.max_scores = dict(self.scorecard)
        self.state = {
            "customers": [],
            "simulations": [],
            "twins": []
        }

    def deduct_score(self, category, amount, reason):
        if category in self.scorecard:
            self.scorecard[category] = max(0, self.scorecard[category] - amount)
            self.errors.append(f"[{category} -{amount}] {reason}")

    def log_warning(self, reason):
        self.warnings.append(reason)

    def request(self, method, path, **kwargs):
        start = time.time()
        url = f"{BASE_URL}{path}"
        try:
            r = self.session.request(method, url, timeout=15, **kwargs)
            total_time = time.time() - start
            server_time = r.elapsed.total_seconds()
            
            # DNS and Connection times are not natively separated in requests without lower-level hooks,
            # so we approximate connection time as the difference if needed, but we capture what's available.
            self.metrics.append({
                "path": path,
                "method": method,
                "status_code": r.status_code,
                "total_response_time": total_time,
                "server_processing_time": server_time,
                "payload_size": len(r.content),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return r
        except Exception as e:
            total_time = time.time() - start
            self.metrics.append({
                "path": path,
                "method": method,
                "status_code": 0,
                "total_response_time": total_time,
                "server_processing_time": 0,
                "payload_size": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            self.errors.append(f"Request failed: {method} {path} - {str(e)}")
            return None

    def section_1_response_metrics(self):
        print("\n=== SECTION 1: RESPONSE METRICS ===")
        if not self.metrics:
            print("No metrics gathered yet.")
            return

        latencies = [m["total_response_time"] * 1000 for m in self.metrics]
        latencies.sort()
        n = len(latencies)
        p50 = latencies[int(n * 0.5)] if n > 0 else 0
        p90 = latencies[int(n * 0.9)] if n > 0 else 0
        p95 = latencies[int(n * 0.95)] if n > 0 else 0
        p99 = latencies[int(n * 0.99)] if n > 0 else 0

        print(f"P50: {p50:.2f}ms")
        print(f"P90: {p90:.2f}ms")
        print(f"P95: {p95:.2f}ms")
        print(f"P99: {p99:.2f}ms")

        with open(OUT_DIR / "response_metrics.json", "w") as f:
            json.dump({
                "p50_ms": p50,
                "p90_ms": p90,
                "p95_ms": p95,
                "p99_ms": p99,
                "metrics": self.metrics
            }, f, indent=2)

        for m in self.metrics:
            lat = m["total_response_time"] * 1000
            if lat > 2000:
                self.log_warning(f"CRITICAL LATENCY: {m['method']} {m['path']} took {lat:.2f}ms (>2000ms)")
                self.deduct_score("Performance", 1, f"Critical latency on {m['path']}")
            elif lat > 500:
                self.log_warning(f"WARNING LATENCY: {m['method']} {m['path']} took {lat:.2f}ms (>500ms)")

    def section_2_openapi_validation(self):
        print("\n=== SECTION 2: OPENAPI VALIDATION ===")
        r = self.request("GET", "/openapi.json")
        if not r or r.status_code != 200:
            self.deduct_score("API Reliability", 10, "Failed to fetch OpenAPI spec")
            return
        
        self.openapi_spec = r.json()
        paths = self.openapi_spec.get("paths", {})
        print(f"Discovered {len(paths)} paths in OpenAPI spec.")
        
        schema_mismatches = []
        for path, methods in paths.items():
            if "get" in methods:
                # Basic reachability test for GET endpoints without path parameters
                if "{" not in path:
                    resp = self.request("GET", path)
                    if not resp or resp.status_code >= 500:
                        schema_mismatches.append({"path": path, "issue": "Unreachable or 500 Error"})
                        self.deduct_score("API Reliability", 1, f"Endpoint {path} unreachable")
        
        with open(OUT_DIR / "schema_mismatch_report.json", "w") as f:
            json.dump(schema_mismatches, f, indent=2)
        if schema_mismatches:
            print(f"Found {len(schema_mismatches)} schema mismatches.")

    def section_3_customer_validation(self):
        print("\n=== SECTION 3: CUSTOMER VALIDATION ===")
        r = self.request("GET", "/api/v1/customers?limit=10")
        if not r or r.status_code != 200:
            self.deduct_score("Data Quality", 5, "Failed to fetch customers")
            return
        
        customers = r.json().get("data", [])
        if not customers:
            customers = r.json()
        
        if not isinstance(customers, list):
            self.deduct_score("Data Quality", 5, "Customer list is not an array")
            return

        self.state["customers"] = customers

        for cust in customers:
            cid = cust.get("id")
            if not cid:
                continue

            # Profile
            pr = self.request("GET", f"/api/v1/customers/{cid}/profile")
            if pr and pr.status_code == 200:
                prof = pr.json()
                if prof.get("customer_id") != cid:
                    self.deduct_score("Data Quality", 1, f"Profile customer_id mismatch for {cid}")
            
            # Preferences
            pref_r = self.request("GET", f"/api/v1/customers/{cid}/preferences")
            if pref_r and pref_r.status_code == 200:
                pref = pref_r.json()
                if pref.get("customer_id") != cid:
                    self.deduct_score("Data Quality", 1, f"Preference customer_id mismatch for {cid}")

            # Segments
            seg_r = self.request("GET", f"/api/v1/customers/{cid}/segments")
            if seg_r and seg_r.status_code == 200:
                segs = seg_r.json()
                if not isinstance(segs, list):
                    self.deduct_score("Data Quality", 1, f"Segments for {cid} is not a list")

            # Events
            ev_r = self.request("GET", f"/api/v1/customers/{cid}/events")
            if ev_r and ev_r.status_code == 200:
                evs = ev_r.json().get("data", []) if isinstance(ev_r.json(), dict) else ev_r.json()
                for ev in evs:
                    if ev.get("customer_id") != cid:
                        self.deduct_score("Data Quality", 1, f"Event customer_id mismatch for {cid}")

    def section_4_digital_twin_validation(self):
        print("\n=== SECTION 4: DIGITAL TWIN VALIDATION ===")
        valid_statuses = {"building", "built", "stale", "rebuilding", "failed"}
        
        for cust in self.state.get("customers", [])[:5]:
            cid = cust.get("id")
            r = self.request("GET", f"/api/v1/twins/{cid}")
            if not r or r.status_code != 200:
                self.deduct_score("Twin Engine", 2, f"Failed to fetch twin for {cid}")
                continue
            
            twin = r.json()
            if twin.get("customer_id") != cid:
                self.deduct_score("Twin Engine", 2, f"Twin customer_id mismatch for {cid}")

            status = twin.get("status")
            if status not in valid_statuses:
                self.deduct_score("Twin Engine", 2, f"Invalid twin status '{status}' for {cid}")

            # Score bounds check
            for score_field in ["engagement_score", "loyalty_score", "confidence_score", "staleness_score"]:
                val = twin.get(score_field)
                if val is not None and not (0 <= val <= 1):
                    self.deduct_score("Twin Engine", 1, f"Twin {score_field} out of bounds: {val}")

            if twin.get("lifetime_value", 0) < 0:
                self.deduct_score("Twin Engine", 1, f"Twin lifetime_value negative for {cid}")

            if not twin.get("interest_graph"):
                self.deduct_score("Twin Engine", 1, f"Twin interest_graph empty for {cid}")

            self.state["twins"].append(twin)

    def section_5_prediction_validation(self):
        print("\n=== SECTION 5: PREDICTION VALIDATION ===")
        for cust in self.state.get("customers", [])[:5]:
            cid = cust.get("id")
            
            # General predictions
            r = self.request("GET", f"/api/v1/twins/{cid}/predictions")
            if r and r.status_code == 200:
                preds = r.json()
                if not preds:
                    self.deduct_score("Prediction Engine", 1, f"No predictions found for {cid}")
                else:
                    for pred in preds:
                        if "timestamp" not in pred:
                            self.deduct_score("Prediction Engine", 1, f"Prediction missing timestamp for {cid}")
                        if "confidence" not in pred:
                            self.deduct_score("Prediction Engine", 1, f"Prediction missing confidence for {cid}")
                        if pred.get("value") is None:
                            self.deduct_score("Prediction Engine", 1, f"Prediction value is null for {cid}")

            # Specific bounded checks
            c_r = self.request("GET", f"/api/v1/twins/{cid}/predictions/churn")
            if c_r and c_r.status_code == 200:
                c_val = c_r.json().get("churn_probability", c_r.json().get("value", 0))
                if not (0 <= c_val <= 1):
                    self.deduct_score("Prediction Engine", 2, f"Churn probability out of bounds: {c_val}")

            l_r = self.request("GET", f"/api/v1/twins/{cid}/predictions/ltv")
            if l_r and l_r.status_code == 200:
                l_val = l_r.json().get("projected_ltv", l_r.json().get("value", 0))
                if l_val < 0:
                    self.deduct_score("Prediction Engine", 2, f"Projected LTV negative: {l_val}")

    def section_6_simulation_validation(self):
        print("\n=== SECTION 6: SIMULATION VALIDATION ===")
        # Create simulation
        payload = {
            "name": f"Framework Test Sim {uuid.uuid4().hex[:6]}",
            "type": "campaign",
            "monte_carlo_iterations": 100,
            "confidence_level": 0.95,
            "time_horizon_days": 30,
            "parameters": {"growth_rate": 0.05}
        }
        r = self.request("POST", "/api/v1/simulations", json=payload)
        if not r or r.status_code >= 400:
            self.deduct_score("Simulation Engine", 10, "Failed to create simulation")
            return
        
        sim = r.json()
        sim_id = sim.get("id")
        
        # Wait/check progress
        success = False
        for _ in range(5):
            stat_r = self.request("GET", f"/api/v1/simulations/{sim_id}/status")
            if stat_r and stat_r.status_code == 200:
                status = stat_r.json().get("status")
                if status == "completed":
                    success = True
                    break
            time.sleep(1)
        
        if not success:
            self.log_warning(f"Simulation {sim_id} did not complete in time.")
        
        res_r = self.request("GET", f"/api/v1/simulations/{sim_id}/results")
        if res_r and res_r.status_code == 200:
            results = res_r.json()
            if not results:
                self.deduct_score("Simulation Engine", 5, "Simulation results empty")
            else:
                # Check for NaN / Infinity
                res_str = json.dumps(results).lower()
                if "nan" in res_str or "infinity" in res_str:
                    self.deduct_score("Simulation Engine", 5, "Simulation results contain NaN/Infinity")
                
                # Check specifics (roi, revenue)
                if "roi" not in res_str and "revenue" not in res_str:
                    self.deduct_score("Simulation Engine", 2, "Simulation results missing ROI/Revenue keys")

    def section_7_twin_agent_simulation_validation(self):
        print("\n=== SECTION 7: TWIN -> AGENT -> SIMULATION ===")
        # 1. Read customer twin
        if not self.state["customers"]:
            self.log_warning("No customers available for Section 7")
            return
        
        cid = self.state["customers"][0].get("id")
        twin_r1 = self.request("GET", f"/api/v1/twins/{cid}")
        if not twin_r1 or twin_r1.status_code != 200:
            self.deduct_score("Simulation Engine", 5, "Could not fetch twin for Sec 7")
            return
            
        # Run sim 1
        sim_payload = {
            "name": f"TwinTest1 {uuid.uuid4().hex[:6]}",
            "type": "campaign",
            "monte_carlo_iterations": 10,
            "target_customer_id": cid
        }
        sr1 = self.request("POST", "/api/v1/simulations", json=sim_payload)
        out1 = sr1.json() if sr1 else {}

        # 2. Modify customer characteristic
        # Using a PUT to update customer logic if supported, or creating an event
        ev_payload = {
            "event_type": "purchase", "event_name": "massive_purchase",
            "customer_id": cid, "channel": "web", "source": "api",
            "event_properties": {"value": 999999}
        }
        self.request("POST", "/api/v1/events", json=ev_payload)
        self.request("POST", f"/api/v1/twins/{cid}/rebuild", json={})
        time.sleep(1)

        # Run sim 2
        sim_payload["name"] = f"TwinTest2 {uuid.uuid4().hex[:6]}"
        sr2 = self.request("POST", "/api/v1/simulations", json=sim_payload)
        out2 = sr2.json() if sr2 else {}

        # 4. Verify output changes
        if out1 == out2 and out1:
            self.deduct_score("Simulation Engine", 10, "FAIL: Simulation output unchanged after twin modification. Disconnected from twin engine.")

    def section_8_business_logic_validation(self):
        print("\n=== SECTION 8: BUSINESS LOGIC VALIDATION ===")
        if len(self.state.get("twins", [])) < 2:
            self.log_warning("Not enough twins for comparative logic validation.")
            return

        twins = self.state["twins"]
        twins.sort(key=lambda x: x.get("loyalty_score", 0), reverse=True)
        high_loyalty = twins[0]
        low_loyalty = twins[-1]

        hl_cid = high_loyalty.get("customer_id")
        ll_cid = low_loyalty.get("customer_id")

        hl_cr = self.request("GET", f"/api/v1/twins/{hl_cid}/predictions/churn")
        ll_cr = self.request("GET", f"/api/v1/twins/{ll_cid}/predictions/churn")

        if hl_cr and ll_cr and hl_cr.status_code == 200 and ll_cr.status_code == 200:
            hl_churn = hl_cr.json().get("churn_probability", 0)
            ll_churn = ll_cr.json().get("churn_probability", 0)

            if hl_churn > ll_churn:
                self.deduct_score("Twin Engine", 5, "High loyalty customer has higher churn than low loyalty customer.")

    def section_9_edge_case_testing(self):
        print("\n=== SECTION 9: EDGE CASE TESTING ===")
        
        # Invalid UUID
        r = self.request("GET", "/api/v1/customers/invalid-uuid-string")
        if r and r.status_code == 500:
            self.deduct_score("API Reliability", 2, "Invalid UUID returned 500 instead of 400/404")
            
        # Empty Payload
        r = self.request("POST", "/api/v1/customers", json={})
        if r and r.status_code == 500:
            self.deduct_score("API Reliability", 2, "Empty POST payload returned 500")

        # Extreme values
        payload = {
            "name": "Extreme Simulation",
            "type": "campaign",
            "monte_carlo_iterations": 999999999999999
        }
        r = self.request("POST", "/api/v1/simulations", json=payload)
        if r and r.status_code == 500:
            self.deduct_score("API Reliability", 2, "Extreme value returned 500 instead of 400 validation error")

    def section_10_load_testing(self):
        print("\n=== SECTION 10: LOAD TESTING ===")
        levels = [10, 50, 100, 250, 500] 
        
        def fetch_health():
            start = time.time()
            try:
                r = requests.get(f"{BASE_URL}/health", timeout=10)
                return {"success": r.status_code == 200, "latency": time.time() - start}
            except:
                return {"success": False, "latency": time.time() - start}

        for level in levels:
            successes = 0
            failures = 0
            latencies = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(level, 100)) as executor:
                futures = [executor.submit(fetch_health) for _ in range(level)]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res["success"]:
                        successes += 1
                    else:
                        failures += 1
                    latencies.append(res["latency"])
            
            avg_lat = statistics.mean(latencies) if latencies else 0
            print(f"Load Level {level}: {successes} OK, {failures} ERR, Avg Latency: {avg_lat*1000:.2f}ms")
            if failures > 0:
                self.deduct_score("Performance", 2, f"Load test failures at level {level}")
            if avg_lat > 1.0:
                self.deduct_score("Performance", 1, f"Load test avg latency > 1s at level {level}")

    def section_11_regression_detection(self):
        print("\n=== SECTION 11: REGRESSION DETECTION ===")
        baseline_file = OUT_DIR / "baseline.json"
        
        current_state = {
            "endpoint_count": len(self.openapi_spec.get("paths", {})) if self.openapi_spec else 0,
            "avg_latency": statistics.mean([m["total_response_time"] for m in self.metrics]) if self.metrics else 0
        }
        
        if baseline_file.exists():
            with open(baseline_file, "r") as f:
                baseline = json.load(f)
                
            if current_state["endpoint_count"] < baseline.get("endpoint_count", 0):
                self.log_warning("REGRESSION: Endpoints missing compared to baseline")
            if current_state["avg_latency"] > baseline.get("avg_latency", 0) * 1.5:
                self.log_warning("REGRESSION: Performance degraded > 50% compared to baseline")
                self.deduct_score("Performance", 2, "Performance regression detected")
                
        # Save new baseline
        with open(baseline_file, "w") as f:
            json.dump(current_state, f, indent=2)

    def section_12_final_scorecard(self):
        print("\n=== SECTION 12: FINAL SCORECARD ===")
        total_score = sum(self.scorecard.values())
        max_possible = sum(self.max_scores.values())
        
        print(f"Backend Health Score: {total_score} / {max_possible}")
        for k, v in self.scorecard.items():
            print(f"  {k}: {v}/{self.max_scores[k]}")
            
        status = "PASS"
        if total_score < 60:
            status = "FAIL"
        elif total_score < 85:
            status = "WARNING"
            
        print(f"\nFINAL STATUS: {status}")
        
        report = {
            "timestamp": NOW,
            "status": status,
            "total_score": total_score,
            "max_possible": max_possible,
            "categories": self.scorecard,
            "errors": self.errors,
            "warnings": self.warnings
        }
        
        with open(OUT_DIR / "scorecard.json", "w") as f:
            json.dump(report, f, indent=2)
            
        print(f"\nReport saved to: {OUT_DIR / 'scorecard.json'}")

    def run_all(self):
        print("Starting PROMETHEUS Backend Validation Framework...")
        self.section_2_openapi_validation()
        self.section_3_customer_validation()
        self.section_4_digital_twin_validation()
        self.section_5_prediction_validation()
        self.section_6_simulation_validation()
        self.section_7_twin_agent_simulation_validation()
        self.section_8_business_logic_validation()
        self.section_9_edge_case_testing()
        self.section_1_response_metrics()  # Put 1 here to gather all previous requests
        self.section_10_load_testing()
        self.section_11_regression_detection()
        self.section_12_final_scorecard()

if __name__ == "__main__":
    validator = PrometheusValidator()
    validator.run_all()
