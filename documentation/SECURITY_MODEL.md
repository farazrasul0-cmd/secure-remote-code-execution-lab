# Security Model & Threat Mitigation (Defense-in-Depth)
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 2.0.0  
**Domain:** Kernel Isolation, Virtualization Security & STRIDE Analysis  
**Academic Target:** Cybersecurity & Operating Systems Architecture  

---

## 1. Threat Landscape & Security Philosophy

Executing untrusted, user-submitted code in a shared multi-tenant environment is an intrinsically high-risk undertaking. The attacker has arbitrary code execution privileges within the sandbox by design. 

Therefore, our security philosophy assumes that:
1. **The application layer is compromised:** The user will write code specifically designed to breach isolation, exploit the operating system kernel, or saturate shared physical resources.
2. **Single-layer defenses always fail:** Relying solely on container isolation (Docker) is insufficient because containers share the host Linux kernel (`ring 0`). A single kernel zero-day vulnerability can lead to complete host takeover.
3. **Defense-in-Depth is mandatory:** Every request must navigate a 6-layer concentric defensive perimeter before and during execution.

---

## 2. Concentric 6-Layer Security Perimeter

```
                      Layer 1: Network Ingress Microsegmentation
                     ┌──────────────────────────────────────────┐
                     │ • Nginx TLS Termination                  │
                     │ • Redis Sliding Window Rate Limiting     │
                     │ • Kubernetes Zero-Trust NetworkPolicies  │
                     └────────────────────┬─────────────────────┘
                                          │
                      Layer 2: Unprivileged Execution Envelope
                     ┌────────────────────┴─────────────────────┐
                     │ • Dedicated System UID/GID (10001:10001) │
                     │ • Root privileges dropped                │
                     │ • PodSecurityStandards: Restricted       │
                     └────────────────────┬─────────────────────┘
                                          │
                      Layer 3: Namespace Isolation
                     ┌────────────────────┴─────────────────────┐
                     │ • PID Namespace (isolated PID 1)         │
                     │ • Mount Namespace (pivot_root)           │
                     │ • Network Namespace (--net=none)         │
                     │ • IPC / UTS Namespaces                   │
                     └────────────────────┬─────────────────────┘
                                          │
                      Layer 4: cgroups v2 Resource Governance
                     ┌────────────────────┴─────────────────────┐
                     │ • cpu.max (0.5 core CFS quota)           │
                     │ • memory.max (128 MB hard ceiling)       │
                     │ • memory.swap.max = 0 (Swap suppressed)  │
                     │ • pids.max = 64 (Fork bomb mitigation)   │
                     └────────────────────┬─────────────────────┘
                                          │
                      Layer 5: Seccomp-BPF Syscall Whitelisting
                     ┌────────────────────┴─────────────────────┐
                     │ • ~350 dangerous syscalls blocked        │
                     │ • ptrace, bpf, mount, clone3 denied      │
                     │ • Immediate SIGKILL / EPERM on breach    │
                     └────────────────────┬─────────────────────┘
                                          │
                      Layer 6: Micro-VM Hardware Hypervisor (KVM)
                     ┌────────────────────┴─────────────────────┐
                     │ • Ring -1 hardware virtualization        │
                     │ • Guest OS kernel memory boundary        │
                     │ • Sub-5ms Firecracker-style boot         │
                     └──────────────────────────────────────────┘
```

---

## 3. Detailed Mechanism Specifications

### 3.1 Resource Governance via cgroups v2
The Linux control groups v2 subsystem enforces deterministic resource allocations:
- **CPU CFS Bandwidth Slicing:**
  Configured as `cpu_period=100000` ($100\text{ms}$) and `cpu_quota=50000` ($50\text{ms}$). Regardless of how many compute threads an untrusted script creates, the kernel scheduler preempts the cgroup after $50\text{ms}$ per window, restricting total CPU utilization to exactly 0.5 CPU cores.
- **Memory Ceiling & Swap Disablement:**
  Configured as `mem_limit="128m"` and `memswap_limit="128m"`. Disabling swap (`memory.swap.max = 0`) prevents malicious programs from thrashing disk I/O. If allocations exceed 128 MB, the kernel OOM killer terminates the sandbox immediately.
- **Process Bomb Defeat:**
  Configured as `pids.max=64`. Fork bombs (`:(){ :|:& };:`) are neutralized because all calls to `fork()` or `clone()` beyond 64 active tasks fail instantaneously with `EAGAIN`.

### 3.2 System Call Filtering via Seccomp-BPF
Linux Secure Computing Mode (Seccomp) compiled with Berkeley Packet Filters (BPF) inspects system call numbers before switching the CPU from unprivileged mode (`ring 3`) into kernel mode (`ring 0`):
- **Whitelisted Syscalls:** Only standard POSIX compute syscalls (`read`, `write`, `exit_group`, `mmap`, `brk`, `fstat`, `rt_sigreturn`) are allowed.
- **Prohibited Syscalls:** All administrative and kernel-exploit primitives (`ptrace`, `bpf`, `mount`, `umount2`, `chroot`, `sys_admin`, `reboot`, `kexec_load`, `perf_event_open`) are intercepted and rejected with `EPERM` or `SIGSYS`.

### 3.3 Network Namespace Isolation (`--net=none`)
To prevent Server-Side Request Forgery (SSRF), internal port scanning, cryptocurrency mining, and botnet propagation:
- The container is initialized in an air-gapped network namespace with only a loopback interface (`lo`) that is disconnected from the host stack.
- In Kubernetes, `NetworkPolicies` enforce a default-deny-all ingress and egress rule on worker pods, rendering socket calls completely unroutable.

### 3.4 Filesystem Immutability & Memory RAM Disk (`tmpfs`)
- The container root filesystem (`rootfs`) is mounted strictly **read-only** (`--read-only`).
- User source code and compiled binaries reside entirely within an in-memory `tmpfs` RAM disk mounted at `/tmp` with flags `noexec,nosuid,nodev,size=16m`.
- Untrusted code cannot persist malware or modify system binaries on disk.

### 3.5 Micro-VM Hardware Virtualization (`MicroVMSandbox`)
While containers share the host Linux kernel, Micro-VMs leverage hardware virtualization extensions (Intel VT-x / AMD-V) through `/dev/kvm`:
- Each untrusted execution runs inside an isolated, stripped-down guest Linux kernel.
- Hardware memory management units (EPT / NPT) enforce hardware-level page table isolation.
- An attacker breaking through the guest kernel remains contained inside the unprivileged hypervisor process (`ring -1`), completely isolated from the host operating system.

---

## 4. STRIDE Threat Model & Containment Matrix

| Threat Category | Attack Vector | Countermeasure & Enforcement Layer | Result |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Forging JWT tokens to submit code as other users | Signed JWT tokens with Argon2id password hashing and DB secret rotation | 401 Unauthorized |
| **Tampering** | Overwriting system binaries or modifying neighboring containers | Read-only root filesystem (`--read-only`) + ephemeral 16MB in-memory `tmpfs` | 100% Contained |
| **Repudiation** | Denying malicious code execution or resource abuse | Immutable PostgreSQL audit log recording `user_id`, IP, code hash, duration, and telemetry | Audit Trail Intact |
| **Information Disclosure** | Probing `/etc/shadow`, AWS IAM metadata (`169.254.169.254`), or host network | Air-gapped network namespace (`--net=none`) + unprivileged user (`uid=1001`) | Network Unreachable |
| **Denial of Service** | Fork bombs, memory bombs, infinite loops, and disk filling | cgroups v2 (`cpu.max`, `memory.max`, `pids.max`) + worker watchdog timer (`SIGKILL`) | TLE / MLE / EAGAIN |
| **Elevation of Privilege** | Exploiting kernel vulnerabilities (`dirty_pipe`, `ptrace`) | Seccomp-BPF blocking `ptrace`/`bpf` + dropped capabilities (`CAP_DROP ALL`) + KVM Micro-VM | EPERM / Hardware Trapped |
