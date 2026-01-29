import { prisma } from "@/lib/prisma";
import { LEAGUES } from "../../config/leagues";

interface PageProps {
    params: Promise<{ league: string }>;
}

export default async function ResultsPage({ params }: PageProps) {
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

    // 리그 정보 조회
    const leagueDb = await prisma.sl_leagues.findFirst({
        where: { slug: leagueSlug }
    });

    // 종료된 경기 조회
    const now = new Date();
    const games = await prisma.sl_games.findMany({
        where: {
            league_id: leagueDb?.id,
            status: {
                in: ["STATUS_FINAL", "STATUS_FULL_TIME", "STATUS_POSTPONED"]
            },
            game_date: {
                lte: now // 미래 데이터(테스트/더미) 제외
            },
            // 실제 팀 정보가 존재하는 데이터만 조회 (Broken Link 방지)
            sl_teams_sl_games_home_team_idTosl_teams: { isNot: null },
            sl_teams_sl_games_away_team_idTosl_teams: { isNot: null }
        },
        include: {
            sl_teams_sl_games_home_team_idTosl_teams: true,
            sl_teams_sl_games_away_team_idTosl_teams: true
        },
        orderBy: {
            game_date: 'desc'
        },
        take: 20
    });

    return (
        <div className="resultsContainer">
            <div className="pageHeader">
                <h1>{leagueConfig.name} 경기결과</h1>
                <p className="leagueInfo">
                    {leagueConfig.sport} • {leagueConfig.country}
                </p>
            </div>

            <div className="resultsContent">
                <div className="filterSection">
                    <div className="gameCount">최근 {games.length}개의 기록</div>
                </div>

                <div className="resultsList">
                    {games.length > 0 ? (
                        games.map((game) => {
                            const homeScore = game.home_score ?? 0;
                            const awayScore = game.away_score ?? 0;
                            const isHomeWinner = homeScore > awayScore;
                            const isAwayWinner = awayScore > homeScore;
                            const isDraw = homeScore === awayScore && game.status !== "STATUS_SCHEDULED";

                            return (
                                <div key={game.id.toString()} className="resultCard premium">
                                    <div className="cardTop">
                                        <span className="statusTag">
                                            {game.status === "STATUS_POSTPONED" ? "경기 연기" : "경기 종료"}
                                        </span>
                                        <span className="gameTime">
                                            {new Intl.DateTimeFormat('ko-KR', {
                                                month: 'short',
                                                day: 'numeric',
                                                weekday: 'short',
                                                hour: '2-digit',
                                                minute: '2-digit'
                                            }).format(new Date(game.game_date))}
                                        </span>
                                    </div>

                                    <div className="matchRow">
                                        <div className={`teamBlock home ${isHomeWinner ? "winner" : ""}`}>
                                            <div className="teamInfo">
                                                <div className="logoWrapper">
                                                    {game.sl_teams_sl_games_home_team_idTosl_teams?.logo_url ? (
                                                        <img src={game.sl_teams_sl_games_home_team_idTosl_teams.logo_url} alt="" />
                                                    ) : (
                                                        <div className="emptyLogo">{game.sl_teams_sl_games_home_team_idTosl_teams?.name?.charAt(0) || "?"}</div>
                                                    )}
                                                </div>
                                                <span className="name">{game.sl_teams_sl_games_home_team_idTosl_teams?.name || "알 수 없는 팀"}</span>
                                            </div>
                                            <span className="scoreDisplay">{homeScore}</span>
                                        </div>

                                        <div className="divider">
                                            <span className="vsText">VS</span>
                                        </div>

                                        <div className={`teamBlock away ${isAwayWinner ? "winner" : ""}`}>
                                            <div className="teamInfo">
                                                <div className="logoWrapper">
                                                    {game.sl_teams_sl_games_away_team_idTosl_teams?.logo_url ? (
                                                        <img src={game.sl_teams_sl_games_away_team_idTosl_teams.logo_url} alt="" />
                                                    ) : (
                                                        <div className="emptyLogo">{game.sl_teams_sl_games_away_team_idTosl_teams?.name?.charAt(0) || "?"}</div>
                                                    )}
                                                </div>
                                                <span className="name">{game.sl_teams_sl_games_away_team_idTosl_teams?.name || "알 수 없는 팀"}</span>
                                            </div>
                                            <span className="scoreDisplay">{awayScore}</span>
                                        </div>
                                    </div>

                                    <div className="cardFooter">
                                        <span className="venue">
                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                                            {game.score_detail && typeof game.score_detail === 'object' && !Array.isArray(game.score_detail) && (game.score_detail as any).venue
                                                ? (game.score_detail as any).venue
                                                : "장소 미정"}
                                        </span>
                                    </div>
                                </div>
                            );
                        })
                    ) : (
                        <div className="emptyState">
                            <p>최근 경기 결과가 없습니다.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

