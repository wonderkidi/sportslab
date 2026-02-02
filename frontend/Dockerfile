# 1. 의존성 설치 단계 (node:20으로 변경)
FROM node:20-alpine AS deps
WORKDIR /app
# 패키지 파일 복사
COPY package.json package-lock.json ./

# ▼▼▼ [수정 핵심] Prisma 스키마 폴더를 npm ci 전에 먼저 복사해야 합니다! ▼▼▼
COPY prisma ./prisma/

# 이제 스키마가 존재하므로 postinstall(prisma generate)이 성공합니다.
RUN npm ci

# 2. 빌드 단계
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Next.js 텔레메트리 비활성화
ENV NEXT_TELEMETRY_DISABLED=1

# 빌드 실행 (Prisma Client 생성 포함)
RUN npm run build

# 3. 실행 단계 (최종 이미지)
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 정적 파일 복사 (필요 시 주석 해제)
# COPY --from=builder /app/public ./public

# Standalone 모드 결과물 복사
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# ▼▼▼ [주의] 컨테이너 내부 포트가 3010으로 설정되어 있습니다.
EXPOSE 3010
ENV PORT=3010

CMD ["node", "server.js"]