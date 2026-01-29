"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PropsWithChildren, useState } from "react";
import { LEAGUES } from "./config/leagues";

export default function SiteShell({ children }: PropsWithChildren) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  // 현재 어느 섹션(일정, 결과, 선수)에 있는지 파악
  const getCurrentSection = () => {
    if (pathname?.startsWith("/results")) return "results";
    if (pathname?.startsWith("/players")) return "players";
    return "schedule"; // 기본값은 일정
  };

  const section = getCurrentSection();

  return (
    <div className="page">
      <div className="container">
        <header className="header">
          <div className="headerCard">
            <div className="headerTop">
              <div>
                <h1 className="headerTitle">SPORTS LAB</h1>
              </div>
            </div>
            <nav className="tabNav">
              <Link
                href="/"
                className={`tabButton ${pathname === "/" ? "tabActive" : "tabInactive"
                  }`}
              >
                전체
              </Link>
              <Link
                href="/schedule"
                className={`tabButton ${pathname?.startsWith("/schedule")
                  ? "tabActive"
                  : "tabInactive"
                  }`}
              >
                경기일정
              </Link>
              <Link
                href="/results"
                className={`tabButton ${pathname?.startsWith("/results")
                  ? "tabActive"
                  : "tabInactive"
                  }`}
              >
                경기결과
              </Link>
              <Link
                href="/players"
                className={`tabButton ${pathname?.startsWith("/players") ? "tabActive" : "tabInactive"
                  }`}
              >
                선수조회
              </Link>
            </nav>
          </div>
        </header>

        <div className="contentWrap">
          <aside className="sideColumn">
            <div className="stickyWrap">
              <div className="leagueList">
                {LEAGUES.map((league) => (
                  <Link
                    key={league.slug}
                    href={`/${section}/${league.slug}`}
                    className="leagueButton"
                  >
                    {league.name}
                  </Link>
                ))}
              </div>
            </div>
          </aside>

          <div className="contentGrid">
            <main className="main">
              {children}
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
              {LEAGUES.map((league) => (
                <Link
                  key={league.slug}
                  href={`/${section}/${league.slug}`}
                  className="drawerButton"
                  onClick={() => setMobileOpen(false)}
                >
                  {league.name}
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
