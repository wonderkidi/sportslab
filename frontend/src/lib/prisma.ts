import { PrismaClient } from "@prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import { Pool } from "pg";
import "dotenv/config";

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

const connectionString =
  process.env.DATABASE_URL ??
  (() => {
    const {
      DB_USER,
      DB_PASSWORD,
      DB_HOST,
      DB_PORT,
      DB_NAME,
    } = process.env;
    if (!DB_USER || !DB_PASSWORD || !DB_HOST || !DB_PORT || !DB_NAME) {
      throw new Error(
        "Missing DATABASE_URL or DB_* env vars (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)."
      );
    }
    const user = encodeURIComponent(DB_USER);
    const pass = encodeURIComponent(DB_PASSWORD);
    return `postgresql://${user}:${pass}@${DB_HOST}:${DB_PORT}/${DB_NAME}`;
  })();

const pool = new Pool({ connectionString });
const adapter = new PrismaPg(pool);

export const prisma =
    globalForPrisma.prisma ||
    new PrismaClient({ adapter });

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;
