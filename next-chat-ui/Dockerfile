FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder

WORKDIR /app
ARG CLINIC_PASSWORD=""
ARG LOGIN_PASSWORD=""
ENV NEXT_TELEMETRY_DISABLED=1
ENV CLINIC_PASSWORD=${CLINIC_PASSWORD}
ENV LOGIN_PASSWORD=${LOGIN_PASSWORD}

COPY --from=deps /app/node_modules ./node_modules
COPY . ./

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
