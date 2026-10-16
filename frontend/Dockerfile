# Build the web app; Caddy (deploy/Caddyfile) serves the result and forwards /api/ to the backend.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=/api/v1/
ARG VITE_DEMO_MODE=true
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL VITE_DEMO_MODE=$VITE_DEMO_MODE
RUN npm run build

FROM caddy:2.8-alpine
COPY --from=build /app/dist /srv
