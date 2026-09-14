"""Janitor Daemon Reaping Orphaned and Stale Execution Containers."""

import logging
from datetime import UTC, datetime

from docker.errors import DockerException

import docker
from worker.config import worker_settings

logger = logging.getLogger("rce_worker.janitor")


class JanitorReaper:
    """Detects and forcefully removes sandbox containers exceeding maximum operational lease."""

    def __init__(
        self,
        max_lease_seconds: int = worker_settings.CONTAINER_MAX_LEASE_SECONDS,
        client: docker.DockerClient | None = None,
    ):
        self.max_lease_seconds = max_lease_seconds
        self._client = client

    @property
    def client(self) -> docker.DockerClient | None:
        """Lazy initialization of Docker client."""
        if self._client is None:
            try:
                self._client = docker.from_env()
                self._client.ping()
            except Exception:
                self._client = None
        return self._client

    def reap_stale_containers(self) -> list[str]:
        """Scan active sandbox containers and terminate those exceeding lease."""
        reaped_ids = []
        if not self.client:
            return reaped_ids

        try:
            # Query containers managed by the RCE engine
            filters = {"label": ["sandbox_type=isolated"]}
            containers = self.client.containers.list(all=True, filters=filters)

            now = datetime.now(UTC)

            for container in containers:
                try:
                    created_raw = container.attrs.get("Created")
                    if not created_raw:
                        continue

                    # Parse Docker timestamp (ISO 8601 with nanoseconds)
                    # Example: 2026-09-11T12:34:56.789123456Z
                    created_clean = created_raw[:26].rstrip("Z")
                    created_dt = datetime.fromisoformat(created_clean).replace(
                        tzinfo=UTC
                    )

                    age_seconds = (now - created_dt).total_seconds()

                    if age_seconds > self.max_lease_seconds:
                        logger.warning(
                            "Reaping orphan container %s (age: %.1fs > lease: %ds)",
                            container.short_id,
                            age_seconds,
                            self.max_lease_seconds,
                        )
                        container.remove(force=True, v=True)
                        reaped_ids.append(container.id)

                except Exception as exc:
                    logger.error("Failed to reap container %s: %s", container.id, exc)

        except DockerException as dex:
            logger.error("Docker daemon error during janitor reap: %s", dex)

        return reaped_ids
