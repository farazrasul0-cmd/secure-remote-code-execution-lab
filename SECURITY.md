# Security Policy

## 1. Supported Versions

We actively maintain and provide security patches for the following versions:

| Version | Supported          | Security State |
| ------- | ------------------ | -------------- |
| 2.0.x   | :white_check_mark: | Active Production Release |
| 1.5.x   | :white_check_mark: | Security Fixes Only |
| < 1.5.0 | :x:                | Deprecated |

---

## 2. Threat Model & Sandbox Isolation Invariants

The **Secure Real-Time Remote Code Execution Platform** is specifically designed to execute untrusted, potentially adversarial user code. As such, the platform enforces invariant defense-in-depth isolation layers:

1. **Linux Namespaces (`CLONE_NEWPID`, `CLONE_NEWNET`, `CLONE_NEWNS`, `CLONE_NEWIPC`, `CLONE_NEWUTS`, `CLONE_NEWUSER`):**
   - Untrusted code runs as PID 1 inside an isolated process namespace.
   - Network namespace is instantiated with `--net=none`, blocking all egress, socket binding, LAN probing, and metadata server queries.
2. **Resource Constraints (cgroups v2):**
   - CPU: CFS bandwidth quota limited to 0.5 CPU cores (`cpu.max="50000 100000"`).
   - Memory: Hard ceiling of 128 MB with swap strictly disabled (`memory.swap.max = 0`). Exceeding memory triggers the Linux kernel OOM killer (`SIGKILL`, exit 137).
   - Process Limits: Maximum 64 tasks (`pids.max=64`), defeating fork bombs (`EAGAIN`).
3. **Kernel System Call Filtering (Seccomp-BPF):**
   - System calls enabling container breakouts, kernel module loading, raw sockets, or process snooping (`ptrace`, `bpf`, `mount`, `chroot`, `sys_admin`, `clone3`) are intercepted and denied at Ring 0.
4. **Filesystem Immutability:**
   - Root filesystem is mounted read-only (`--read-only`). Ephemeral execution files are restricted to a size-capped 16 MB in-memory `tmpfs` RAM disk mounted with `noexec,nosuid,nodev`.
5. **Micro-VM Hypervisor Boundary (Phase 9):**
   - When running under the `MicroVMSandbox` driver, execution is fenced within a lightweight Linux KVM guest hypervisor boundary, providing Ring -1 hardware virtualization isolation.

---

## 3. Reporting a Vulnerability

We treat all security vulnerabilities with utmost seriousness. If you discover a security vulnerability or sandbox breakout technique, **please do not open a public issue.**

Instead, please report vulnerabilities by emailing:
`security-advisory@secure-rce-lab.org` (or directly contact project maintainer: `faraz.rasul@alumni.cmu.edu`)

### Vulnerability Report Contents
To facilitate rapid triage, please provide:
1. **Attack Type:** Sandbox breakout, privilege escalation, CPU/RAM starvation, network leakage, or denial of service.
2. **Step-by-Step Proof of Concept (PoC):** Minimal reproducible script (Python, C/C++, Rust, Go) demonstrating the containment violation.
3. **Observed vs. Expected Behavior:** Details on what kernel or host resources were accessible.
4. **Environment Details:** Host OS kernel version, Docker version, cgroups v2 mount configuration, and sandbox driver utilized (`DOCKER`, `PROCESS`, `MICROVM`).

### Coordinated Disclosure Timeline
- **Initial Response:** Within 24 hours acknowledging receipt.
- **Triage & Reproduction:** Within 72 hours with an initial severity rating (CVSS v3.1).
- **Remediation & Patch:** Within 14 days, followed by a coordinated public security release.
