# Stage 1: Build frontend
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend-vite/package.json frontend-vite/package-lock.json* ./
RUN npm ci
COPY frontend-vite/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend-vite/dist

# Generate synthetic data if not present
RUN python data/generate_synthetic.py 2>/dev/null || true

EXPOSE 8510

CMD ["streamlit", "run", "app.py", "--server.port", "8510", "--server.headless", "true", "--server.address", "0.0.0.0"]
