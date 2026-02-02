# 1. 의존성 설치 단계 (node:20으로 변경)
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
COPY prisma ./prisma/
RUN npm ci

# 2. 빌드 단계
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Next.js 텔레메트리 비활성화
ENV NEXT_TELEMETRY_DISABLED=1

# ▼▼▼ [추가] 빌드 시점에 외부에서 DB 주소를 받기 위한 설정 ▼▼▼
ARG DATABASE_URL
ENV DATABASE_URL=$DATABASE_URL

# 빌드 실행 (이때 DB에 접속해서 데이터를 가져옵니다)
RUN npm run build

# 3. 실행 단계 (최종 이미지)
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3010
ENV PORT=3010

CMD ["node", "server.js"]