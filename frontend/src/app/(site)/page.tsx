import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { LEAGUES } from "./config/leagues";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  // 메인 페이지에 표시할 주요 리그들
  const kblLeague = LEAGUES.find((league) => league.slug === "kbl");
  const baseLeagues = LEAGUES.filter(
    (league) => league.slug !== "k-league" && league.slug !== "kbl"
  );
  const featuredLeagues = [kblLeague, ...baseLeagues]
    .filter(
      (league): league is (typeof LEAGUES)[number] => Boolean(league)
    )
    .slice(0, 9);

  // 각 리그별 최신 경기 결과 가져오기
  const leagueCards = await Promise.all(
    featuredLeagues.map(async (league) => {
      // DB에서 리그 정보 조회
      const leagueDb = await prisma.sl_leagues.findFirst({
        where: { slug: league.slug },
      });

      // 최신 종료된 경기 1건 조회
      const lastGame = leagueDb ? await prisma.sl_games.findFirst({
        where: {
          league_id: leagueDb.id,
          status: { in: ["STATUS_FINAL", "STATUS_FULL_TIME"] },
          game_date: { lte: new Date() }, // 미래 데이터 제외
          sl_teams_sl_games_home_team_idTosl_teams: { isNot: null }, // 팀 정보 필수
          sl_teams_sl_games_away_team_idTosl_teams: { isNot: null }
        },
        include: {
          sl_teams_sl_games_home_team_idTosl_teams: true,
          sl_teams_sl_games_away_team_idTosl_teams: true
        },
        orderBy: { game_date: "desc" }
      }) : null;

      return {
        ...league,
        lastGame,
      };
    })
  ).then((cards) =>
    cards.sort((a, b) => Number(Boolean(b.lastGame)) - Number(Boolean(a.lastGame)))
  );

  return (
    <section className="cardGrid">
      {leagueCards.map((card, index) => {
        const game = card.lastGame;
        const homeTeam = game?.sl_teams_sl_games_home_team_idTosl_teams;
        const awayTeam = game?.sl_teams_sl_games_away_team_idTosl_teams;
        const homeName = homeTeam?.code || homeTeam?.name || "Home";
        const awayName = awayTeam?.code || awayTeam?.name || "Away";
        const homeLogo = homeTeam?.logo_url || null;
        const awayLogo = awayTeam?.logo_url || null;
        const highlight = game
          ? `${homeName} ${game.home_score} - ${game.away_score} ${awayName}`
          : "진행된 경기 없음";
        const detail = game
          ? new Intl.DateTimeFormat('ko-KR', { month: '2-digit', day: '2-digit' }).format(new Date(game.game_date)) + " FINAL"
          : "업데이트 예정";

        return (
          <Link
            key={card.slug}
            href={`/results/${card.slug}`}
            className="card cardLink"
            style={{ animationDelay: `${index * 90}ms` }}
          >
            <div className="cardGlow" />
            <div className="cardHeader">
              <div>
                <h2 className="cardTitle">{card.name}</h2>
              </div>
            </div>
            <div className="cardBody">
              {game && (
                <p className="cardDetail cardDetailCenter">{detail}</p>
              )}
              {game ? (
                <div className="scoreboard">
                  <div className="scoreTeam">
                    <div className="scoreLogo">
                      {homeLogo ? (
                        <img src={homeLogo} alt={homeName} />
                      ) : (
                        <span className="scoreFallback">{homeName.charAt(0)}</span>
                      )}
                    </div>
                    <span className="scoreName">{homeName}</span>
                  </div>
                  <div className="scoreCenter">
                    <span className="scoreValue">
                      {game.home_score} - {game.away_score}
                    </span>
                    <span className="scoreVs">VS</span>
                  </div>
                  <div className="scoreTeam">
                    <div className="scoreLogo">
                      {awayLogo ? (
                        <img src={awayLogo} alt={awayName} />
                      ) : (
                        <span className="scoreFallback">{awayName.charAt(0)}</span>
                      )}
                    </div>
                    <span className="scoreName">{awayName}</span>
                  </div>
                </div>
              ) : (
                <p className="cardHighlight">{highlight}</p>
              )}
              {!game && <p className="cardDetail">{detail}</p>}
            </div>
          </Link>
        );
      })}
    </section>
  );
}
