import Link from "next/link";
import { prisma } from "@/lib/prisma";

type PlayerPageProps = {
    params: Promise<{ league: string; playerId: string }>;
};

export default async function PlayerPage({ params }: PlayerPageProps) {
    const { league, playerId: playerIdStr } = await params;
    const playerId = BigInt(playerIdStr);

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
                <h2>선수를 찾을 수 없습니다</h2>
                <Link href={`/players/${league}`}>선수 목록으로 돌아가기</Link>
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
        <div className="playerDetailWrap">
            <div className="detailTop">
                <Link href={`/players/${league}`} className="backIcon" aria-label="선수 목록">
                    back
                </Link>
            </div>

            <h4 className="titPage">선수 상세 정보</h4>

            <section className="playerInfo">
                <div className="playerTeam">
                    <div className="teamBadge">{currentSquad?.sl_teams?.name || "소속 미정"}</div>
                    <div className="teamSub">PLAYER ID: {playerIdStr} ({league.toUpperCase()})</div>
                </div>

                <div className="playerBasic">
                    <div className="playerPhoto">
                        {player.photo_url ? (
                            <img src={player.photo_url} alt={player.name} />
                        ) : "PHOTO"}
                    </div>
                    <ul className="playerMeta">
                        <li>
                            <strong>선수명:</strong> <span>{player.name}</span>
                        </li>
                        <li>
                            <strong>등번호:</strong> <span>No.{currentSquad?.jersey_number || "-"}</span>
                        </li>
                        <li>
                            <strong>생년월일:</strong> <span>{player.birth_date ? new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(player.birth_date)) : "-"}</span>
                        </li>
                        <li>
                            <strong>포지션:</strong> <span>{currentSquad?.position || "-"}</span>
                        </li>
                        <li>
                            <strong>신장/체중:</strong> <span>{player.height_cm ? `${player.height_cm}cm` : "-"}/{player.weight_kg ? `${player.weight_kg}kg` : "-"}</span>
                        </li>
                        <li>
                            <strong>국적:</strong> <span>{player.nationality || "-"}</span>
                        </li>
                        {/* 비정형 데이터 표시 */}
                        {Object.entries(biometrics).map(([key, value]) => (
                            <li key={key}>
                                <strong>{key}:</strong> <span>{String(value)}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            </section>

            <section className="playerRecords">
                <h6 className="sectionTitle">{currentSquad?.sl_seasons?.year} 성적</h6>
                <div className="tableWrap">
                    <table className="tbl">
                        <thead>
                            <tr>
                                <th>팀명</th>
                                {currentStats?.stats && typeof currentStats.stats === 'object' && Object.keys(currentStats.stats as any).map(statKey => (
                                    <th key={statKey}>{statKey}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>{currentStats?.sl_teams?.name || "-"}</td>
                                {currentStats?.stats && typeof currentStats.stats === 'object' && Object.values(currentStats.stats as any).map((statValue, idx) => (
                                    <td key={idx}>{String(statValue)}</td>
                                ))}
                                {!currentStats && <td colSpan={10} className="emptyRow">기록이 없습니다.</td>}
                            </tr>
                        </tbody>
                    </table>
                </div>

                <h6 className="sectionTitle">최근 경기 기록</h6>
                <div className="tableWrap">
                    <table className="tbl">
                        <thead>
                            <tr>
                                <th>일자</th>
                                <th>상대</th>
                                <th>결과</th>
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
                                    <tr key={stat.id}>
                                        <td>{new Intl.DateTimeFormat('ko-KR', { month: '2-digit', day: '2-digit' }).format(new Date(game.game_date))}</td>
                                        <td>{opponent}</td>
                                        <td>{game.home_score}:{game.away_score}</td>
                                        <td>
                                            {stat.stats && typeof stat.stats === 'object' && Object.entries(stat.stats as any).slice(0, 3).map(([k, v]) => `${k}:${v}`).join(', ')}
                                        </td>
                                    </tr>
                                );
                            }) : (
                                <tr>
                                    <td colSpan={4} className="emptyRow">기록이 없습니다.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
}

