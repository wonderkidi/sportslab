import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { LEAGUES } from "../../../config/leagues";
import SafeImage from "@/components/SafeImage";
import UnderConstructionCard from "@/components/UnderConstructionCard";

type PlayerPageProps = {
    params: Promise<{ league: string; playerId: string }>;
};

export default async function PlayerPage({ params }: PlayerPageProps) {
    const { league, playerId: playerIdStr } = await params;
    const playerId = BigInt(playerIdStr);
    const leagueConfig = LEAGUES.find(l => l.slug === league);
    const isNba = league === "nba";
    if (league === "k-league") {
        return (
            <div className="leagueSelectionContainer">
                <UnderConstructionCard
                    title="K LEAGUE"
                    highlight="K League 데이터 준비중"
                    detail="정확한 데이터 제공을 위해 준비 중입니다."
                />
            </div>
        );
    }

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
                        <SafeImage
                            src={player.photo_url}
                            alt={player.name}
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
                                    {isNba ? (
                                        <>
                                            <th>시간</th>
                                            <th>야투</th>
                                            <th>야투율(%)</th>
                                            <th>3점슛</th>
                                            <th>3점슛율(%)</th>
                                            <th>자유투</th>
                                            <th>자유투율(%)</th>
                                            <th>리바운드</th>
                                            <th>어시스트</th>
                                            <th>블록</th>
                                            <th>스틸</th>
                                            <th>파울</th>
                                            <th>턴오버</th>
                                            <th>득점</th>
                                        </>
                                    ) : (
                                        <th>기록</th>
                                    )}
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
                                    const rawStats = (stat.stats as any)?.stats;
                                    const statsList = Array.isArray(rawStats) ? rawStats : [];

                                    return (
                                        <tr key={stat.id.toString()}>
                                            <td className="dateCell">{new Intl.DateTimeFormat('ko-KR', { month: '2-digit', day: '2-digit' }).format(new Date(game.game_date))}</td>
                                            <td className="oppCell">{opponent}</td>
                                            {isNba ? (
                                                <>
                                                    <td className="statBrief">{statsList[0] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[1] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[2] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[3] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[4] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[5] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[6] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[7] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[8] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[9] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[10] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[11] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[12] ?? "-"}</td>
                                                    <td className="statBrief">{statsList[13] ?? "-"}</td>
                                                </>
                                            ) : (
                                                <td className="statBrief">
                                                    {stat.stats && typeof stat.stats === 'object' && Object.entries(stat.stats as any).slice(0, 3).map(([k, v]) => `${k}:${v}`).join(', ')}
                                                </td>
                                            )}
                                        </tr>
                                    );
                                }) : (
                                    <tr>
                                        <td colSpan={isNba ? 16 : 3} className="emptyRow">최근 경기 기록이 없습니다.</td>
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

