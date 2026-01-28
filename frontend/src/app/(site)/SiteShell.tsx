"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PropsWithChildren, useState } from "react";

const tabs = [
  { label: "메인", active: true },
  { label: "경기결과", active: false },
  { label: "커뮤니티", active: false },
];

const leagues = [
  "MLB",
  "NBA",
  "EPL",
  "NFA",
  "NHL",
  "UCL",
  "IPL",
  "K-LEAGUE",
  "SERIE A",
  "LA LIGA",
  "BUNDESLIGA",
];

const toSlug = (league: string) =>
  league
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

export default function SiteShell({ children }: PropsWithChildren) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const isDetail = pathname?.startsWith("/detail/");

  return (
    <div className="page">
      <div className="container">
        <header className="header">
          <div className="headerCard">
            <div className="headerTop">
              <div>
                <p className="headerLabel">SportsLab Live</p>
                <h1 className="headerTitle">SPORTS LAB</h1>
              </div>
              <div className="headerActions">
                <div className="livePill">
                  <span className="pulseDot" />
                  LIVE UPDATE MOCK
                </div>
                <button
                  type="button"
                  onClick={() => setMobileOpen(true)}
                  className="leagueToggle"
                >
                  리그 보기
                </button>
              </div>
            </div>
            <nav className="tabNav">
              {tabs.map((tab) => (
                <button
                  key={tab.label}
                  className={`tabButton ${tab.active ? "tabActive" : "tabInactive"}`}
                  type="button"
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </header>

        <div className={`contentGrid ${collapsed ? "contentGridCollapsed" : ""}`}>
          <aside className="sideColumn">
            <div className="stickyWrap">
              <div className={`leagueList ${collapsed ? "leagueListCollapsed" : ""}`}>
                <button
                  type="button"
                  onClick={() => setCollapsed((prev) => !prev)}
                  className="leagueCollapseBtn"
                  aria-label={collapsed ? "확장" : "축소"}
                >
                  {collapsed ? "→" : "←"}
                </button>
                {leagues.map((league) => (
                  <Link
                    key={league}
                    href={`/detail/${toSlug(league)}`}
                    className="leagueButton"
                  >
                    {league}
                  </Link>
                ))}
              </div>
            </div>
          </aside>

          <main className="main">
            <section className={isDetail ? "detailGrid" : "cardGrid"}>
              {children}
            </section>
          </main>
        </div>
      </div>

      {mobileOpen && (
        <div className="overlay">
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="overlayBackdrop"
            aria-label="Close league menu"
          />
          <div className="drawer">
            <div className="drawerHeader">
              <h2 className="drawerTitle">Leagues</h2>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="drawerClose"
              >
                닫기
              </button>
            </div>
            <div className="drawerList">
              {leagues.map((league) => (
                <Link
                  key={league}
                  href={`/detail/${toSlug(league)}`}
                  className="drawerButton"
                  onClick={() => setMobileOpen(false)}
                >
                  {league}
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
