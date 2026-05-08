# Stage 1: Build the React frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# Stage 2: Build the Python backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY src/ ./src/
COPY styles/ ./styles/
COPY schemas/ ./schemas/
COPY archetypes.yml .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /web/dist ./web/dist

# Environment variables
ENV PYTHONPATH="/app/src"
ENV RWS_DATABASE_URL="sqlite:////app/rws.db"
ENV PORT=8000

# Expose port
EXPOSE 8000

# Start script
CMD ["python", "-m", "ruwritingstyles.api"]
