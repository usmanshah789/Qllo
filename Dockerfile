# One image, one service: Node builds the React app, Python serves both it and
# the API. That keeps the deployment to a single URL with no CORS to configure.

FROM node:20-slim AS ui
WORKDIR /ui
# Copy the manifests first so npm ci is cached until dependencies change.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=ui /ui/dist ./frontend_dist

# The container layout is not the repo layout, so point the app at both
# explicitly rather than relying on paths relative to the source tree.
ENV FRONTEND_DIST=/app/frontend_dist \
    DATA_DIR=/data \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Render supplies PORT; the default keeps `docker run` working locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
