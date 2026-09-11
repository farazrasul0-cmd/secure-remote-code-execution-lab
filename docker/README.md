# Docker Sandbox Environments
## Secure Real-Time Remote Code Execution Laboratory Platform

This directory contains base images and security profiles for untrusted execution sandboxes:

- `python/Dockerfile`: Unprivileged Alpine-based Python 3.11 runtime (`uid=1001`, `gid=1001`).
- `python/seccomp-profile.json`: Custom Seccomp-BPF policy whitelisting standard library system calls and dropping dangerous calls (`ptrace`, `bpf`, `mount`).

### Build Instructions
```bash
docker build -t lab-sandbox-python:3.11 ./docker/python
```
