import os

import docker
from worker.sandbox.base import BaseSandbox
from worker.sandbox.docker_sandbox import DockerSandbox
from worker.sandbox.microvm_sandbox import MicroVMCapabilities, MicroVMSandbox
from worker.sandbox.models import SandboxDriverType
from worker.sandbox.process_sandbox import ProcessSandbox


class SandboxFactory:
    """Factory creating appropriate sandbox engine based on environment capabilities and configuration."""

    @staticmethod
    def create_sandbox(
        driver_type: SandboxDriverType | str = SandboxDriverType.AUTO,
        force_process: bool = False,
        seccomp_path: str | None = None,
        vcpus: int = 1,
        mem_size_mib: int = 128,
    ) -> BaseSandbox:
        """Instantiate requested sandbox driver with intelligent capability fallback.

        Selection Priority (AUTO mode):
        1. MicroVMSandbox (if /dev/kvm and hardware virtualization available)
        2. DockerSandbox (if Docker daemon socket reachable)
        3. ProcessSandbox (fallback unprivileged subprocess isolation)
        """
        if force_process:
            return ProcessSandbox()

        driver_str = str(driver_type).lower()

        # 1. Explicit Driver Requests
        if driver_str == SandboxDriverType.PROCESS or driver_str == "process":
            return ProcessSandbox()

        if driver_str == SandboxDriverType.MICROVM or driver_str == "microvm":
            return MicroVMSandbox(vcpus=vcpus, mem_size_mib=mem_size_mib)

        if driver_str == SandboxDriverType.DOCKER or driver_str == "docker":
            try:
                client = docker.from_env()
                client.ping()
                profile_path = (
                    seccomp_path if os.path.exists(seccomp_path or "") else None
                )
                return DockerSandbox(seccomp_profile_path=profile_path)
            except Exception:
                return ProcessSandbox()

        # 2. AUTO Mode: Capability Discovery & Negotiation
        if MicroVMCapabilities.is_kvm_available():
            return MicroVMSandbox(vcpus=vcpus, mem_size_mib=mem_size_mib)

        try:
            client = docker.from_env()
            client.ping()
            profile_path = seccomp_path if os.path.exists(seccomp_path or "") else None
            return DockerSandbox(seccomp_profile_path=profile_path)
        except Exception:
            # Universal fallback to ProcessSandbox
            return ProcessSandbox()
