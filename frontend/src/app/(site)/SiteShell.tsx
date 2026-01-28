"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PropsWithChildren, useState } from "react";
import { LEAGUES } from "./config/leagues";

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
            </div>
            <nav className="tabNav">
              <Link
                href="/"
                className={`tabButton ${
                  pathname === "/" ? "tabActive" : "tabInactive"
                }`}
              >
                전체
              </Link>
              <Link
                href="/detail/kbo"
                className={`tabButton ${
                  pathname?.startsWith("/detail")
                    ? "tabActive"
                    : "tabInactive"
                }`}
              >
                경기일정・결과
              </Link>
              <Link
                href="/players"
                className={`tabButton ${
                  pathname === "/players" ? "tabActive" : "tabInactive"
                }`}
              >
                선수조회
              </Link>
              <Link
                href="/community"
                className={`tabButton ${
                  pathname === "/community" ? "tabActive" : "tabInactive"
                }`}
              >
                커뮤니티
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
              {LEAGUES.map((league) => (
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
