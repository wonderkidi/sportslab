import { prisma } from "@/lib/prisma";
import { LEAGUES } from "../../config/leagues";
import UnderConstructionCard from "@/components/UnderConstructionCard";

interface PageProps {
    params: Promise<{ league: string }>;
}

export default async function SchedulePage({ params }: PageProps) {
    const { league: leagueSlug } = await params;

    const leagueConfig = LEAGUES.find((l) => l.slug === leagueSlug);

    if (leagueSlug === "k-league") {
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

    if (!leagueConfig) {
        return (
            <div className="emptyState">
                <h2>리그를 찾을 수 없습니다</h2>
                <p>올바른 리그를 선택해주세요.</p>
            </div>
        );
    }

    // 리그 정보 조회
    const leagueDb = await prisma.sl_leagues.findFirst({
        where: { slug: leagueSlug }
    });

    // 예정된 경기 조회
    const games = await prisma.sl_games.findMany({
        where: {
            league_id: leagueDb?.id,
            status: {
                in: ["STATUS_SCHEDULED", "STATUS_FIRST_HALF", "STATUS_SECOND_HALF", "STATUS_IN_PROGRESS"]
            },
            game_date: {
                gte: new Date()
            }
        },
        include: {
            sl_teams_sl_games_home_team_idTosl_teams: true,
            sl_teams_sl_games_away_team_idTosl_teams: true
        },
        orderBy: {
            game_date: 'asc'
        },
        take: 20
    });

    return (
        <div className="scheduleContainer">
            <div className="pageHeader">
                <h1>{leagueConfig.name} 경기일정</h1>
                <p className="leagueInfo">
                    {leagueConfig.sport} • {leagueConfig.country}
                </p>
            </div>

            <div className="scheduleContent">
                <div className="filterSection">
                    <div className="gameCount">총 {games.length}개의 예정된 경기</div>
                </div>

                <div className="scheduleList">
                    {games.length > 0 ? (
                        games.map((game) => (
                            <div key={game.id.toString()} className="scheduleCard">
                                <div className="scheduleDate">
                                    {new Intl.DateTimeFormat('ko-KR', {
                                        year: 'numeric',
                                        month: '2-digit',
                                        day: '2-digit',
                                        weekday: 'short',
                                        hour: '2-digit',
                                        minute: '2-digit',
                                        hour12: false
                                    }).format(new Date(game.game_date))}
                                </div>
                                <div className="matchInfo">
                                    <div className="team">
                                        <div className="teamLogo">
                                            {game.sl_teams_sl_games_home_team_idTosl_teams?.logo_url ? (
                                                <img src={game.sl_teams_sl_games_home_team_idTosl_teams.logo_url} alt="" />
                                            ) : "🏟️"}
                                        </div>
                                        <div className="teamName">
                                            {game.sl_teams_sl_games_home_team_idTosl_teams?.name || "홈팀"}
                                        </div>
                                    </div>
                                    <div className="vs">VS</div>
                                    <div className="team">
                                        <div className="teamLogo">
                                            {game.sl_teams_sl_games_away_team_idTosl_teams?.logo_url ? (
                                                <img src={game.sl_teams_sl_games_away_team_idTosl_teams.logo_url} alt="" />
                                            ) : "⚾"}
                                        </div>
                                        <div className="teamName">
                                            {game.sl_teams_sl_games_away_team_idTosl_teams?.name || "원정팀"}
                                        </div>
                                    </div>
                                </div>
                                <div className="venue">
                                    {game.score_detail && typeof game.score_detail === 'object' && !Array.isArray(game.score_detail) && (game.score_detail as any).venue
                                        ? `경기장: ${(game.score_detail as any).venue}`
                                        : "장소 미정"}
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="emptyState">
                            <p>예정된 경기가 없습니다.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

