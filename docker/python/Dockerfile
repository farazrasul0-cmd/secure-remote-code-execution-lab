# ==============================================================================
# Hardened Ephemeral Python 3.11 Sandbox Runtime
# Base: Alpine Linux (Minimal Attack Surface ~50MB)
# ==============================================================================

FROM python:3.11-alpine

# Enforce unbuffered I/O and disable bytecode generation
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create unprivileged sandbox user and group (UID 1001, GID 1001)
RUN addgroup -g 1001 sandboxgroup && \
    adduser -u 1001 -G sandboxgroup -s /bin/sh -D sandboxuser

# Create workspace scratch directory
WORKDIR /sandbox
RUN chown -R sandboxuser:sandboxgroup /sandbox

# Switch permanently to unprivileged user
USER sandboxuser

# Default command
CMD ["python3", "-c", "print('Secure Sandbox Ready')"]
