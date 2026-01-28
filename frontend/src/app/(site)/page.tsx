"use client";

import Link from "next/link";

const cards = [
  { league: "MLB", highlight: "LAD 6 - 5 NYY", detail: "Extra Innings" },
  { league: "NBA", highlight: "LAL 112 - 107 BOS", detail: "4Q 2:11" },
  { league: "NFL", highlight: "KC 24 - 21 SF", detail: "Final" },
  { league: "EPL", highlight: "MCI 2 - 0 LIV", detail: "FT" },
  { league: "NHL", highlight: "TOR 3 - 2 NYR", detail: "OT" },
  { league: "UCL", highlight: "RMA 3 - 1 PSG", detail: "FT" },
  { league: "KBO", highlight: "LG 4 - 2 KIA", detail: "9회말 끝내기" },
  { league: "K-LEAGUE", highlight: "ULS 2 - 1 FCB", detail: "FT" },
  { league: "KBL", highlight: "SK 84 - 79 LG", detail: "Final" },
];

const toSlug = (league: string) =>
  league
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

export default function HomePage() {
  return (
    <>
      {cards.map((card, index) => (
        <Link
          key={card.league}
          href={`/detail/${toSlug(card.league)}`}
          className="card cardLink"
          style={{ animationDelay: `${index * 90}ms` }}
        >
          <div className="cardGlow" />
          <div className="cardHeader">
            <div>
              <h2 className="cardTitle">{card.league}</h2>
            </div>
            <span className="cardBadge">경기결과</span>
          </div>
          <div className="cardBody">
            <p className="cardHighlight">{card.highlight}</p>
            <p className="cardDetail">{card.detail}</p>
          </div>
          <div className="cardFooter">
            <span className="footerDot" />
            업데이트 예정
          </div>
        </Link>
      ))}
    </>
  );
}
