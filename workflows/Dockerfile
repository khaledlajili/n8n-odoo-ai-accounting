# n8n Community 2.42.4 — pinned version used throughout the project
# Workflows and credentials are stored in the Neon PostgreSQL database,
# so this Dockerfile only needs the base image with correct env handling.
FROM n8nio/n8n:2.42.4

# Ensure config file permissions are enforced inside the container
ENV N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true

# Render provides PORT; n8n listens on 5678 by default, we let it use that.
# The public URL is injected via WEBHOOK_URL env var at runtime.
EXPOSE 5678
