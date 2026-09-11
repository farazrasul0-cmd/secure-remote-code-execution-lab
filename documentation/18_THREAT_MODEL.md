# Security Threat Model & Defense-in-Depth Specification
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 1.0.0  
**Methodology:** Microsoft STRIDE Model & Defense-in-Depth  
**Domain:** Multi-Tenant Remote Code Execution (RCE) Security  

---

## 1. Security Philosophy & Threat Landscape

Allowing arbitrary users to execute uncompiled or interpreted code on cloud infrastructure is inherently dangerous. By definition, **Remote Code Execution (RCE)** is the capability that attackers strive to achieve through software vulnerabilities; in this platform, RCE is a primary functional feature.

Therefore, our security posture assumes a **Zero-Trust Threat Model**:
> *Every user submission is assumed to be actively adversarial, attempting to crash the host kernel, access internal networks, read other users' data, or escape the container environment.*

---

## 2. STRIDE Threat Analysis

| Threat Category | Description in RCE Context | Risk Level | Architectural Mitigation |
| :--- | :--- | :--- | :--- |
| **Spoofing** | An attacker impersonates another student or injects code under another identity. | Medium | Cryptographic JWT authentication (Argon2id password hashing, signed RS256/HS256 tokens) verified at the API Gateway before job ingestion. |
| **Tampering** | Modifying queued execution payloads, altering telemetry logs, or tampering with database records. | High | In-transit TLS encryption; signed job messages in Redis; PostgreSQL role isolation (worker processes only have `INSERT`/`UPDATE` on submissions; no schema alteration). |
| **Repudiation** | A user submits abusive code (e.g., malware or exploit payloads) and denies responsibility. | Medium | Immutable submission audit logs recorded in PostgreSQL with timestamp, user ID, client IP, source code hash, and execution telemetry. |
| **Information Disclosure** | Untrusted code reading host `/etc/passwd`, cloud instance metadata (e.g., AWS `169.254.169.254`), host environment variables, or adjacent containers. | **Critical** | Complete network isolation (`--net=none`); read-only container rootfs; private ephemeral `tmpfs` storage; no host directory mounts. |
| **Denial of Service (DoS)** | CPU starvation (infinite loops), RAM exhaustion, fork bombs, disk filling, or terminal buffer flooding. | **Critical** | Kernel cgroups v2 (`cpu.max`, `memory.max`, `pids.max`), watchdog wall-clock timers (`SIGKILL`), tmpfs storage ceiling (16MB), and output stream buffer caps (1MB). |
| **Elevation of Privilege** | Container escape, acquiring root permissions on the container host, or accessing the Docker socket. | **Critical** | Unprivileged container user (`uid=1001`), dropping all Linux capabilities (`CAP_DROP ALL`), `no-new-privileges` flag, restricted Seccomp profile, and strict prohibition of Docker socket exposure. |

---

## 3. Attack Vector & Mitigation Matrix

```
[ Untrusted Payload ]
         │
         ▼  (Blocked by API Gateway)
 1. Input Size & Rate Limiter (Max 64KB, Token Bucket)
         │
         ▼  (Blocked by cgroups v2)
 2. Resource Quotas (0.5 CPU, 128MB RAM, 64 PIDs, 5s Timeout)
         │
         ▼  (Blocked by Linux Namespaces)
 3. Namespace Isolation (PID, Mount, IPC, UTS, Network None)
         │
         ▼  (Blocked by Seccomp & Capabilities)
 4. Kernel Attack Surface (Drop ALL Capabilities, Block Dangerous Syscalls)
         │
         ▼  (Blocked by Read-Only VFS)
 5. Storage Isolation (Read-Only Rootfs + Ephemeral RAM tmpfs)
```

### Detailed Vector Analysis

| Attack Vector | Malicious Example | Kernel / System Threat | Applied Mitigation | Defense Layer |
| :--- | :--- | :--- | :--- | :--- |
| **Fork Bomb** | `:(){ :\|:& };:` (Bash)<br>`while True: os.fork()` (Python) | Exhausts host PID table; causes total kernel freeze / crash. | Set `pids.max = 64` in cgroup. Spawning the 65th process fails with `EAGAIN` (`Resource temporarily unavailable`). | Linux cgroups v2 |
| **Memory Bomb** | `a = 'x' * (10**9)` | Allocates all host physical RAM and swap; triggers host-level OOM killer. | Set `memory.max = 128m` and `memory.swap.max = 0`. Container is terminated instantly by the kernel OOM killer (Exit 137). | Linux cgroups v2 |
| **Infinite Busy-Wait** | `while True: pass` | 100% CPU core monopolization; starves legitimate jobs. | Set `cpu.max = "50000 100000"` (50% CFS quota) + Worker watchdog fires `SIGKILL` after 5.0 seconds. | cgroups v2 + POSIX Signal |
| **Disk Exhaustion** | `open('/tmp/fill', 'w').write('0'*10**10)` | Fills physical host SSD; crashes host operating system. | Rootfs is mounted `--read-only`. `/tmp` is a `tmpfs` (RAM disk) strictly capped at 16MB with `noexec,nosuid,nodev`. | Linux VFS / `tmpfs` |
| **Local Network Reconnaissance** | `socket.connect(('192.168.1.1', 80))` | Scans university LAN, cloud metadata APIs (`169.254.169.254`), or Redis/Postgres. | Container launched with `--net=none`. Only the loopback (`lo`) interface exists; all socket calls fail immediately. | Linux Network Namespace |
| **Privilege Escalation** | Setuid binary execution / `sudo` | Attacker gains root inside container; leverages vulnerabilities to break out. | Run container as unprivileged user (`uid=1001`, `gid=1001`); set `--security-opt=no-new-privileges:true`. | POSIX Permissions |
| **Dangerous Syscalls** | `ptrace()`, `bpf()`, `sys_chroot()` | Intercepts host processes or exploits kernel 0-day flaws. | Custom Seccomp profile whitelists only benign standard library syscalls (`read`, `write`, `exit`, etc.); drops `ptrace`, `bpf`, `mount`. | Linux Seccomp-BPF |
| **Terminal / Buffer Flooding** | `while True: print("A"*10000)` | Consumes network bandwidth; crashes browser tab via DOM exhaustion. | Worker truncates stream upon reaching 1 MB (or 10,000 lines); terminates process with `OUTPUT_LIMIT_EXCEEDED`. | Worker Stream Consumer |

---

## 4. Seccomp Syscall Filtering Policy

A strict Seccomp-BPF profile is loaded at container instantiation. By default, any system call not explicitly whitelisted is rejected with `EPERM` (Operation not permitted).

### Explicitly Prohibited Syscalls:
- **Process Tracing & Debugging:** `ptrace`, `process_vm_readv`, `process_vm_writev` (prevents inspecting other processes).
- **Kernel Module & BPF:** `init_module`, `finit_module`, `delete_module`, `bpf` (prevents modifying the running kernel).
- **Filesystem Manipulation:** `mount`, `umount2`, `pivot_root`, `chroot` (prevents breaking out of container mounts).
- **System Administration:** `reboot`, `sethostname`, `setdomainname`, `kexec_load`.
- **Keyring & User Namespaces:** `keyctl`, `add_key`, `unshare`, `clone3` (restricts nested containerization).

---

## 5. Security Incident Response & Audit Logging

Every execution generates an immutable audit record containing:
- Authenticated `user_id` and originating client IP address.
- Complete submitted code snapshot and SHA-256 content hash.
- Linux exit code and termination signal (`SIGKILL`, `SIGSEGV`, `SIGXCPU`).
- Peak cgroup memory and CPU usage statistics.
- Container lifecycle events (creation, start, stop, kill, remove).

Any abnormal termination triggering `SIGSEGV` (Segmentation Fault) or attempts to invoke prohibited system calls are tagged with high priority for administrative review.
