# ==============================================================================
# Multi-Stage Production Dockerfile for Frontend (React 18 + TypeScript + Vite)
# ==============================================================================

# --- Stage 1: Build Environment ---
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies using deterministic clean install
COPY package*.json ./
RUN npm ci

# Copy application source code and compile production bundle
COPY . .
RUN npm run build

# --- Stage 2: Production Web Server ---
FROM nginx:1.27-alpine AS runner

# Security: remove default Nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy custom Nginx configuration with gzip and SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled production static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Production Health Check Probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
