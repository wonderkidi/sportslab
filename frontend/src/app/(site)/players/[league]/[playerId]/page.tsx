import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { LEAGUES } from "../../../config/leagues";

type PlayerPageProps = {
    params: Promise<{ league: string; playerId: string }>;
};

export default async function PlayerPage({ params }: PlayerPageProps) {
    const { league, playerId: playerIdStr } = await params;
    const playerId = BigInt(playerIdStr);
    const leagueConfig = LEAGUES.find(l => l.slug === league);

    // 선수 기본 정보 조회
    const player = await prisma.sl_players.findUnique({
        where: { id: playerId },
        include: {
            sl_player_squads: {
                include: {
                    sl_teams: true,
                    sl_seasons: true
                },
                where: {
                    sl_seasons: {
                        is_current: true
                    }
                }
            },
            sl_player_season_stats: {
                include: {
                    sl_seasons: true,
                    sl_teams: true
                },
                where: {
                    sl_seasons: {
                        is_current: true
                    }
                }
            }
        }
    });

    if (!player) {
        return (
            <div className="emptyState">
                <div className="emptyIcon">👤</div>
                <h2>선수를 찾을 수 없습니다</h2>
                <p>요청하신 선수의 정보를 베이스볼 데이터베이스에서 찾을 수 없습니다.</p>
                <Link href={`/players/${league}`} className="headerBtn" style={{ marginTop: '1.5rem' }}>선수 목록으로 돌아가기</Link>
            </div>
        );
    }

    const currentSquad = player.sl_player_squads[0];
    const currentStats = player.sl_player_season_stats[0];

    // 최근 10경기 기록 조회
    const gameStats = await prisma.sl_player_game_stats.findMany({
        where: { player_id: playerId },
        include: {
            sl_games: {
                include: {
                    sl_teams_sl_games_home_team_idTosl_teams: true,
                    sl_teams_sl_games_away_team_idTosl_teams: true
                }
            }
        },
        orderBy: {
            sl_games: {
                game_date: 'desc'
            }
        },
        take: 10
    });

    const biometrics = player.biometrics as any || {};

    return (
        <div className="playerDetailWrap rise">
            <div className="detailTop">
                <Link href={`/players/${league}`} className="headerBtn">
                    ← 선수 목록
                </Link>
            </div>

            <section className="playerMainInfo">
                <div className="playerVisual">
                    <div className="playerPhotoLarge">
                        <img
                            src={player.photo_url || "/images/noimage.png"}
                            alt={player.name}
                            onError={(e) => {
                                (e.target as HTMLImageElement).src = "/images/noimage.png";
                                (e.target as HTMLImageElement).style.opacity = "0.3";
                            }}
                            style={!player.photo_url ? { opacity: 0.3 } : {}}
                        />
                    </div>
                </div>

                <div className="playerSummary">
                    <div className="playerIdentity">
                        <span className="playerTeamBadge">{currentSquad?.sl_teams?.name || "소속 미정"}</span>
                        <h1 className="playerFullName">{player.name}</h1>
                        <div className="playerContext">
                            {leagueConfig?.name} • {currentSquad?.position || "POS"} • #{currentSquad?.jersey_number || "-"}
                        </div>
                    </div>

                    <div className="playerQuickMeta">
                        <div className="metaItem">
                            <span className="metaLabel">국적</span>
                            <span className="metaValue">{player.nationality || "-"}</span>
                        </div>
                        <div className="metaItem">
                            <span className="metaLabel">신장</span>
                            <span className="metaValue">{player.height_cm ? `${player.height_cm}cm` : "-"}</span>
                        </div>
                        <div className="metaItem">
                            <span className="metaLabel">체중</span>
                            <span className="metaValue">{player.weight_kg ? `${player.weight_kg}kg` : "-"}</span>
                        </div>
                        <div className="metaItem">
                            <span className="metaLabel">생년월일</span>
                            <span className="metaValue">
                                {player.birth_date ? new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(player.birth_date)) : "-"}
                            </span>
                        </div>
                    </div>
                </div>
            </section>

            <div className="recordsGrid">
                <section className="recordsSection">
                    <h3 className="sectionHeading">{currentSquad?.sl_seasons?.year || '현재'} 시즌 성적</h3>
                    <div className="statsTableContainer">
                        <table className="statsTable">
                            <thead>
                                <tr>
                                    <th>팀</th>
                                    {currentStats?.stats && typeof currentStats.stats === 'object' && Object.keys(currentStats.stats as any).map(statKey => (
                                        <th key={statKey}>{statKey}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {currentStats ? (
                                    <tr>
                                        <td className="teamName">{currentStats.sl_teams?.name || "-"}</td>
                                        {Object.values(currentStats.stats as any).map((statValue, idx) => (
                                            <td key={idx}>{String(statValue)}</td>
                                        ))}
                                    </tr>
                                ) : (
                                    <tr>
                                        <td colSpan={10} className="emptyRow">이번 시즌 기록이 아직 없습니다.</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </section>

                <section className="recordsSection">
                    <h3 className="sectionHeading">최근 10경기 기록</h3>
                    <div className="statsTableContainer">
                        <table className="statsTable">
                            <thead>
                                <tr>
                                    <th>일자</th>
                                    <th>상대</th>
                                    <th>스코어</th>
                                    <th>기록</th>
                                </tr>
                            </thead>
                            <tbody>
                                {gameStats.length > 0 ? gameStats.map((stat) => {
                                    const game = stat.sl_games;
                                    if (!game) return null;

                                    const isHome = game.home_team_id === currentSquad?.team_id;
                                    const opponent = isHome
                                        ? game.sl_teams_sl_games_away_team_idTosl_teams?.name
                                        : game.sl_teams_sl_games_home_team_idTosl_teams?.name;

                                    return (
                                        <tr key={stat.id.toString()}>
                                            <td className="dateCell">{new Intl.DateTimeFormat('ko-KR', { month: '2-digit', day: '2-digit' }).format(new Date(game.game_date))}</td>
                                            <td className="oppCell">{opponent}</td>
                                            <td className="scoreCell">{game.home_score}:{game.away_score}</td>
                                            <td className="statBrief">
                                                {stat.stats && typeof stat.stats === 'object' && Object.entries(stat.stats as any).slice(0, 3).map(([k, v]) => `${k}:${v}`).join(', ')}
                                            </td>
                                        </tr>
                                    );
                                }) : (
                                    <tr>
                                        <td colSpan={4} className="emptyRow">최근 경기 기록이 없습니다.</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </section>
            </div>
        </div>
    );
}

