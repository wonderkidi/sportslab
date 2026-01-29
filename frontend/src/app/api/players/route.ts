import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(request: NextRequest) {
    const { searchParams } = new URL(request.url);
    const leagueSlug = searchParams.get("league");

    if (!leagueSlug) {
        return NextResponse.json({ error: "League slug is required" }, { status: 400 });
    }

    try {
        // 리그 정보 및 현재 시즌 조회
        const leagueDb = await prisma.sl_leagues.findFirst({
            where: { slug: leagueSlug },
            include: {
                sl_seasons: {
                    where: { is_current: true },
                    take: 1
                }
            }
        });

        if (!leagueDb || !leagueDb.sl_seasons[0]) {
            return NextResponse.json([]);
        }

        const currentSeason = leagueDb.sl_seasons[0];

        // 해당 리그/시즌의 선수단 조회
        const squads = await prisma.sl_player_squads.findMany({
            where: {
                season_id: currentSeason.id
            },
            include: {
                sl_players: true,
                sl_teams: true
            },
            take: 200, // Increase limit for better search experience
            orderBy: {
                sl_players: {
                    name: 'asc'
                }
            }
        });

        // BigInt serialization handle
        const serializedSquads = JSON.parse(
            JSON.stringify(squads, (key, value) =>
                typeof value === 'bigint' ? value.toString() : value
            )
        );

        return NextResponse.json(serializedSquads);
    } catch (error) {
        console.error("API Players Error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
