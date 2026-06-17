#!/usr/bin/env bash
set -euo pipefail

DOCKER_DAEMON_JSON="/etc/docker/daemon.json"
DOCKER_DNS_1="1.1.1.1"
DOCKER_DNS_2="8.8.8.8"
BASE_IMAGES=(
  "postgres:16-alpine"
  "redis:7-alpine"
  "python:3.12-slim"
  "node:20-alpine"
  "prom/prometheus:v2.50.0"
  "grafana/grafana:11.0.0"
  "mlflow/mlflow:v2.15.1"
)

check_docker_resolution() {
  if ! command -v docker &>/dev/null; then
    echo "[FAIL] Docker is not installed."
    return 1
  fi

  if ! docker info &>/dev/null; then
    echo "[FAIL] Docker daemon is not running or current user lacks permissions."
    return 1
  fi

  echo "[OK] Docker daemon is running."

  local test_image="alpine:latest"
  local output
  output=$(docker pull "$test_image" 2>&1) || true

  if echo "$output" | grep -qi "no such host\|dns\|resolve\|timeout\|TLS"; then
    echo "[FAIL] Docker cannot resolve DNS or pull images."
    echo ""
    echo "  Error: $(echo "$output" | tail -1)"
    return 1
  fi

  echo "[OK] Docker DNS resolution works (pulled $test_image successfully)."
  return 0
}

suggest_daemon_config() {
  echo ""
  echo "=== Suggested Fix: Configure Docker DNS ==="
  echo ""
  echo "  1. Create or edit $DOCKER_DAEMON_JSON:"
  echo ""
  echo '  sudo mkdir -p /etc/docker'
  echo "  cat << 'EOF' | sudo tee $DOCKER_DAEMON_JSON"
  echo '  {'
  echo "    \"dns\": [\"${DOCKER_DNS_1}\", \"${DOCKER_DNS_2}\"],"
  echo '    "dns-opts": ["timeout:2", "attempts:3"],'
  echo '    "max-concurrent-downloads": 10,'
  echo '    "log-driver": "json-file",'
  echo '    "log-opts": {'
  echo '      "max-size": "10m",'
  echo '      "max-file": "3"'
  echo '    }'
  echo '  }'
  echo '  EOF'
  echo ""
  echo "  2. Restart Docker:"
  echo ""
  echo '  sudo systemctl restart docker'
  echo ""
  echo "  3. Verify:"
  echo ""
  echo '  docker run --rm alpine ping -c 1 google.com'
  echo ""
}

suggest_prepull_images() {
  echo ""
  echo "=== Manual Image Pre-pull ==="
  echo ""
  echo "  If DNS issues persist, pull base images manually:"
  echo ""
  for img in "${BASE_IMAGES[@]}"; do
    echo "  docker pull $img"
  done
  echo ""
  echo "  Or use a registry mirror by adding to $DOCKER_DAEMON_JSON:"
  echo ""
  echo '  "registry-mirrors": ["https://mirror.gcr.io", "https://docker-mirror.example.com"]'
  echo ""
}

main() {
  echo "=== Docker DNS Health Check ==="
  echo ""

  if check_docker_resolution; then
    echo ""
    echo "[PASS] Docker DNS is functioning correctly."
    exit 0
  fi

  echo ""
  echo "[INFO] DNS issues detected."
  suggest_daemon_config
  suggest_prepull_images

  echo ""
  echo "=== Quick Test ==="
  echo ""
  echo "After applying the fix, re-run this script to verify:"
  echo "  bash $0"
  echo ""
}

main
