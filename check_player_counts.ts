import { PrismaClient } from '@prisma/client';
import { PrismaPg } from '@prisma/adapter-pg';
import { Pool } from 'pg';
import 'dotenv/config';

async function main() {
    const pool = new Pool({ connectionString: process.env.DATABASE_URL });
    const adapter = new PrismaPg(pool);
    const prisma = new PrismaClient({ adapter });

    const stats = await prisma.$queryRaw`
        SELECT l.name as league_name, COUNT(s.id) as player_count
        FROM sl_player_squads s
        JOIN sl_seasons sea ON s.season_id = sea.id
        JOIN sl_leagues l ON sea.league_id = l.id
        GROUP BY l.name
        ORDER BY player_count DESC
    `;

    console.log(JSON.stringify(stats, (key, value) =>
        typeof value === 'bigint' ? value.toString() : value
        , 2));

    await pool.end();
}

main();
