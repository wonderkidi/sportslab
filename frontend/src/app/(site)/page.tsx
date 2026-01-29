import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { LEAGUES } from "./config/leagues";

export default async function HomePage() {
  // 메인 페이지에 표시할 주요 리그들
  const featuredLeagues = LEAGUES.slice(0, 9);

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
          status: { in: ["STATUS_FINAL", "STATUS_FULL_TIME"] }
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
  );

  return (
    <section className="cardGrid">
      {leagueCards.map((card, index) => {
        const game = card.lastGame;
        const homeName = game?.sl_teams_sl_games_home_team_idTosl_teams?.code || game?.sl_teams_sl_games_home_team_idTosl_teams?.name || "Home";
        const awayName = game?.sl_teams_sl_games_away_team_idTosl_teams?.code || game?.sl_teams_sl_games_away_team_idTosl_teams?.name || "Away";
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
              <span className="cardBadge">최근결과</span>
            </div>
            <div className="cardBody">
              <p className="cardHighlight">{highlight}</p>
              <p className="cardDetail">{detail}</p>
            </div>
            <div className="cardFooter">
              <span className="footerDot" />
              {card.sport.toUpperCase()}
            </div>
          </Link>
        );
      })}
    </section>
  );
}
