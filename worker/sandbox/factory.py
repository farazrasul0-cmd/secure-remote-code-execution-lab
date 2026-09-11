"""Sandbox Factory for Dynamic Runtime Instantiation."""

import os

import docker
from worker.sandbox.base import BaseSandbox
from worker.sandbox.docker_sandbox import DockerSandbox
from worker.sandbox.process_sandbox import ProcessSandbox


class SandboxFactory:
    """Factory creating appropriate sandbox engine based on environment capabilities."""

    @staticmethod
    def create_sandbox(
        force_process: bool = False,
        seccomp_path: str | None = "docker/python/seccomp-profile.json",
    ) -> BaseSandbox:
        """Instantiate DockerSandbox if Docker daemon is available; otherwise fallback to ProcessSandbox."""
        if force_process:
            return ProcessSandbox()

        try:
            client = docker.from_env()
            client.ping()
            profile_path = seccomp_path if os.path.exists(seccomp_path or "") else None
            return DockerSandbox(seccomp_profile_path=profile_path)
        except Exception:
            # Fallback to process-level isolation if Docker daemon is unreachable
            return ProcessSandbox()
