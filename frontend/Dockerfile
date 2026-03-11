FROM node:20-slim AS builder

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy application source
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-slim

WORKDIR /app

# Copy built application and production dependencies
COPY --from=builder /app/build ./build
COPY --from=builder /app/package*.json ./
RUN npm install --omit=dev

# Expose port (default for adapter-node is 3000)
# Note: This assumes @sveltejs/adapter-node is used.
# If adapter-auto is used and it falls back to something else, this might need adjustment.
EXPOSE 3000

# Start command
CMD ["node", "build"]
