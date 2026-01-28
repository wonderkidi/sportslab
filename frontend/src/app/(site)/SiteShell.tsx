"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PropsWithChildren, useState } from "react";

const tabs = [
  { label: "메인", href: "/" },
  { label: "경기결과", href: "/" },
  { label: "커뮤니티", href: "/community" },
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
  const pathname = usePathname();
  const isDetail = pathname?.startsWith("/detail/");

  return (
    <div className="page">
      <div className="container">
        <header className="header">
          <div className="headerCard">
            <div className="headerTop">
              <div>
                <h1 className="headerTitle">SPORTS LAB</h1>
              </div>
              <div className="headerActions">
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
                <Link
                  key={tab.label}
                  href={tab.href}
                  className={`tabButton ${
                    pathname === tab.href ? "tabActive" : "tabInactive"
                  }`}
                >
                  {tab.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        <div className="contentWrap">
          <aside className="sideColumn">
            <div className="stickyWrap">
              <div className="leagueList">
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

          <div className="contentGrid">
            <main className="main">
              <section className={isDetail ? "detailGrid" : "cardGrid"}>
                {children}
              </section>
            </main>
          </div>
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
