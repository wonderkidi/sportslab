import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { LEAGUES } from "../../config/leagues";

interface PageProps {
    params: Promise<{ league: string }>;
}

export default async function PlayersPage({ params }: PageProps) {
    const { league: leagueSlug } = await params;

    const leagueConfig = LEAGUES.find((l) => l.slug === leagueSlug);

    if (!leagueConfig) {
        return (
            <div className="emptyState">
                <h2>리그를 찾을 수 없습니다</h2>
                <p>올바른 리그를 선택해주세요.</p>
            </div>
        );
    }

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

    const currentSeason = leagueDb?.sl_seasons[0];

    // 해당 리그/시즌의 선수단 조회
    const squads = currentSeason ? await prisma.sl_player_squads.findMany({
        where: {
            season_id: currentSeason.id
        },
        include: {
            sl_players: true,
            sl_teams: true
        },
        take: 50,
        orderBy: {
            sl_players: {
                name: 'asc'
            }
        }
    }) : [];

    return (
        <div className="playersContainer">
            <div className="pageHeader">
                <h1>{leagueConfig.name} 선수조회</h1>
                <p className="leagueInfo">
                    {leagueConfig.sport} • {leagueConfig.country}
                </p>
            </div>

            <div className="playersContent">
                <div className="searchSection">
                    <input
                        type="text"
                        placeholder="선수 이름으로 검색..."
                        className="searchInput"
                    />
                    <div className="gameCount">총 {squads.length}명의 선수</div>
                </div>

                <div className="playersList">
                    {squads.length > 0 ? (
                        squads.map((squad) => (
                            <Link
                                key={squad.id}
                                href={`/players/${leagueSlug}/${squad.player_id?.toString()}`}
                                className="playerCard"
                            >
                                <div className="playerPhoto">
                                    {squad.sl_players?.photo_url ? (
                                        <img src={squad.sl_players.photo_url} alt={squad.sl_players.name} />
                                    ) : (
                                        <div className="photoPlaceholder">👤</div>
                                    )}
                                </div>
                                <div className="playerInfo">
                                    <h3 className="playerName">{squad.sl_players?.name || "선수 이름"}</h3>
                                    <p className="playerTeam">{squad.sl_teams?.name || "소속팀"}</p>
                                    <div className="playerStats">
                                        <span>포지션: {squad.position || "미정"}</span>
                                        <span>등번호: {squad.jersey_number || "-"}</span>
                                    </div>
                                </div>
                            </Link>
                        ))
                    ) : (
                        <div className="emptyState">
                            <p>등록된 선수 정보가 없습니다.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

