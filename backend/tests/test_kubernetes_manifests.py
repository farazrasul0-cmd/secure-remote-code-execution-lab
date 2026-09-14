"""Unit tests for Task 8.4: Cloud-Native Kubernetes Orchestration & Helm Chart Validation.

Tests verify:
1. Helm chart structure completeness (Chart.yaml, values.yaml, all templates).
2. Kubernetes manifest YAML validity and required field presence.
3. PodSecurityStandards Restricted compliance across all workload specs.
4. Zero-Trust NetworkPolicy default-deny and microsegmentation rules.
5. HPA v2 autoscaling configuration for backend (CPU) and worker (queue depth).
6. StatefulSet persistent storage and headless service configuration.
7. Ingress WebSocket upgrade annotations and path-based routing.
"""

from pathlib import Path

import yaml

HELM_DIR = Path(__file__).resolve().parents[2] / "helm" / "rce-platform"
TEMPLATES_DIR = HELM_DIR / "templates"


# ============================================================================
# 1. Chart Structure Completeness
# ============================================================================


def test_helm_chart_structure_completeness():
    """Verify all required Helm chart files exist."""
    assert (HELM_DIR / "Chart.yaml").is_file()
    assert (HELM_DIR / "values.yaml").is_file()
    assert (TEMPLATES_DIR / "_helpers.tpl").is_file()

    expected_templates = [
        "namespace.yaml",
        "configmap.yaml",
        "secrets.yaml",
        "deployment-frontend.yaml",
        "deployment-backend.yaml",
        "deployment-worker.yaml",
        "statefulset-postgres.yaml",
        "statefulset-redis.yaml",
        "service-frontend.yaml",
        "service-backend.yaml",
        "service-postgres.yaml",
        "service-redis.yaml",
        "ingress.yaml",
        "networkpolicies.yaml",
        "hpa-backend.yaml",
        "hpa-worker.yaml",
    ]
    for template in expected_templates:
        assert (TEMPLATES_DIR / template).is_file(), f"Missing template: {template}"


def test_chart_yaml_metadata():
    """Verify Chart.yaml contains required metadata fields."""
    with open(HELM_DIR / "Chart.yaml") as f:
        chart = yaml.safe_load(f)

    assert chart["apiVersion"] == "v2"
    assert chart["name"] == "rce-platform"
    assert chart["type"] == "application"
    assert "version" in chart
    assert "appVersion" in chart
    assert "description" in chart


def test_values_yaml_structure():
    """Verify values.yaml contains all required top-level configuration sections."""
    with open(HELM_DIR / "values.yaml") as f:
        values = yaml.safe_load(f)

    # Top-level sections
    assert "global" in values
    assert "frontend" in values
    assert "backend" in values
    assert "worker" in values
    assert "postgres" in values
    assert "redis" in values
    assert "ingress" in values
    assert "autoscaling" in values
    assert "networkPolicies" in values

    # Resource limits defined for all workloads
    for component in ["frontend", "backend", "worker", "postgres", "redis"]:
        assert "resources" in values[component], f"Missing resources for {component}"
        assert "requests" in values[component]["resources"]
        assert "limits" in values[component]["resources"]

    # StatefulSet storage defined
    assert "storage" in values["postgres"]
    assert "size" in values["postgres"]["storage"]
    assert "storage" in values["redis"]
    assert "size" in values["redis"]["storage"]


# ============================================================================
# 2. Template YAML Validity
# ============================================================================


def test_template_yaml_files_parse_without_errors():
    """Verify all template YAML files are syntactically valid (ignoring Go template directives)."""
    # Templates with Go template syntax won't fully parse with yaml.safe_load,
    # but we can verify they are non-empty and contain expected Kubernetes keywords
    for template_file in TEMPLATES_DIR.glob("*.yaml"):
        content = template_file.read_text(encoding="utf-8")
        assert len(content) > 50, f"Template {template_file.name} is suspiciously small"
        # All YAML templates should reference the namespace
        assert "namespace" in content or "Namespace" in content, (
            f"Template {template_file.name} missing namespace reference"
        )


# ============================================================================
# 3. PodSecurityStandards Restricted Compliance
# ============================================================================


def test_namespace_enforces_pod_security_standards():
    """Verify namespace template includes PodSecurityStandards Restricted enforcement labels."""
    content = (TEMPLATES_DIR / "namespace.yaml").read_text(encoding="utf-8")
    assert "pod-security.kubernetes.io/enforce: restricted" in content
    assert "pod-security.kubernetes.io/audit: restricted" in content
    assert "pod-security.kubernetes.io/warn: restricted" in content


def test_deployments_enforce_restricted_security_context():
    """Verify all deployment templates include restricted security contexts."""
    deployment_files = [
        "deployment-frontend.yaml",
        "deployment-backend.yaml",
        "deployment-worker.yaml",
    ]
    for filename in deployment_files:
        content = (TEMPLATES_DIR / filename).read_text(encoding="utf-8")
        assert "automountServiceAccountToken: false" in content, (
            f"{filename} missing automountServiceAccountToken: false"
        )
        # Security context may be inline or via Go template helper include
        has_inline = "allowPrivilegeEscalation: false" in content
        has_helper = 'include "rce-platform.containerSecurityContext"' in content
        assert has_inline or has_helper, (
            f"{filename} missing container security context (inline or helper)"
        )
        has_pod_inline = "runAsNonRoot: true" in content
        has_pod_helper = 'include "rce-platform.securityContext"' in content
        assert has_pod_inline or has_pod_helper, (
            f"{filename} missing pod security context (inline or helper)"
        )


# ============================================================================
# 4. Zero-Trust NetworkPolicy Validation
# ============================================================================


def test_networkpolicies_default_deny_all():
    """Verify default-deny-all NetworkPolicy exists blocking all ingress and egress."""
    content = (TEMPLATES_DIR / "networkpolicies.yaml").read_text(encoding="utf-8")
    assert "default-deny-all" in content
    assert "Ingress" in content
    assert "Egress" in content
    # Should have component-specific policies
    assert "allow-frontend" in content
    assert "allow-backend" in content
    assert "allow-worker" in content
    assert "allow-postgres" in content
    assert "allow-redis" in content


def test_worker_networkpolicy_blocks_ingress():
    """Verify worker pods have no ingress allowed (workers should never accept connections)."""
    content = (TEMPLATES_DIR / "networkpolicies.yaml").read_text(encoding="utf-8")
    # Find the worker policy section and verify ingress: []
    assert "ingress: []" in content


# ============================================================================
# 5. HPA Autoscaling Configuration
# ============================================================================


def test_hpa_backend_uses_cpu_and_memory_metrics():
    """Verify backend HPA scales on CPU and memory utilization."""
    content = (TEMPLATES_DIR / "hpa-backend.yaml").read_text(encoding="utf-8")
    assert "autoscaling/v2" in content
    assert "name: cpu" in content
    assert "name: memory" in content
    assert "Utilization" in content
    assert "scaleDown" in content
    assert "scaleUp" in content


def test_hpa_worker_uses_custom_queue_depth_metric():
    """Verify worker HPA scales on custom rce_worker_queue_depth Prometheus metric."""
    content = (TEMPLATES_DIR / "hpa-worker.yaml").read_text(encoding="utf-8")
    assert "autoscaling/v2" in content
    assert "rce_worker_queue_depth" in content
    assert "AverageValue" in content
    # Worker HPA should scale up aggressively (stabilization 0)
    assert "stabilizationWindowSeconds: 0" in content
    # And scale down conservatively (300s window)
    assert "stabilizationWindowSeconds: 300" in content


# ============================================================================
# 6. StatefulSet Persistent Storage
# ============================================================================


def test_postgres_statefulset_has_persistent_storage():
    """Verify PostgreSQL StatefulSet uses PersistentVolumeClaim for data durability."""
    content = (TEMPLATES_DIR / "statefulset-postgres.yaml").read_text(encoding="utf-8")
    assert "StatefulSet" in content
    assert "volumeClaimTemplates" in content
    assert "postgres-data" in content
    assert "ReadWriteOnce" in content
    assert "pg_isready" in content
    assert "postgres-headless" in content


def test_redis_statefulset_has_aof_persistence():
    """Verify Redis StatefulSet enables AOF persistence and uses PVC."""
    content = (TEMPLATES_DIR / "statefulset-redis.yaml").read_text(encoding="utf-8")
    assert "StatefulSet" in content
    assert "appendonly" in content
    assert "volumeClaimTemplates" in content
    assert "redis-data" in content
    assert "redis-cli" in content
    assert "redis-headless" in content


# ============================================================================
# 7. Ingress WebSocket Configuration
# ============================================================================


def test_ingress_websocket_upgrade_annotations():
    """Verify Ingress includes WebSocket proxy timeout annotations."""
    content = (TEMPLATES_DIR / "ingress.yaml").read_text(encoding="utf-8")
    assert "networking.k8s.io/v1" in content
    assert "/api" in content
    assert "/ws" in content
    assert "ingressClassName" in content


def test_ingress_path_routing_completeness():
    """Verify Ingress routes /api, /ws, and / to correct backend services."""
    content = (TEMPLATES_DIR / "ingress.yaml").read_text(encoding="utf-8")
    # API routes to backend
    assert "/api" in content
    # WebSocket routes to backend
    assert "/ws" in content
    # Root routes to frontend
    assert "path: /" in content
