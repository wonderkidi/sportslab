"use client";

import Link from "next/link";
import { useState, useMemo, useEffect } from "react";
import { LEAGUES } from "../../config/leagues";

interface Player {
    id: string;
    name: string;
    firstname?: string | null;
    lastname?: string | null;
    photo_url: string | null;
}

interface Team {
    id: string;
    name: string;
    code?: string | null;
}

interface Squad {
    id: number;
    player_id: string;
    team_id: string;
    position: string | null;
    jersey_number: number | null;
    sl_players: Player | null;
    sl_teams: Team | null;
}

interface LeagueInfo {
    name: string;
    sport: string;
    country?: string;
}

export default function PlayersPage({ params }: { params: Promise<{ league: string }> }) {
    const [leagueSlug, setLeagueSlug] = useState<string>("");
    const [squads, setSquads] = useState<Squad[]>([]);
    const [leagueInfo, setLeagueInfo] = useState<LeagueInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const teamColorMap: Record<string, string> = {
        SSG: "#fc1c3d",
        WO: "#6b0012",
        LG: "#c30036",
        KT: "#070707",
        NC: "#002c6a",
        HT: "#b50f22",
        SS: "#005bac",
        LT: "#002857",
        OB: "#0f0c29",
        HH: "#ed7100"
    };
    const teamNameColorMap: Record<string, string> = {
        "SSG 랜더스": "#fc1c3d",
        "키움 히어로즈": "#6b0012",
        "LG 트윈스": "#c30036",
        "KT 위즈": "#070707",
        "NC 다이노스": "#002c6a",
        "KIA 타이거즈": "#b50f22",
        "삼성 라이온즈": "#005bac",
        "롯데 자이언츠": "#002857",
        "두산 베어스": "#0f0c29",
        "한화 이글스": "#ed7100"
    };

    useEffect(() => {
        params.then(p => {
            setLeagueSlug(p.league);
            const conf = LEAGUES.find(l => l.slug === p.league);
            if (conf) {
                setLeagueInfo({
                    name: conf.name,
                    sport: conf.sport,
                    country: conf.country
                });
            }

            if (p.league) {
                // Client-side fetch to avoid potential BigInt serialization issues in RSC params
                fetch(`/api/players?league=${p.league}`)
                    .then(res => res.json())
                    .then(data => {
                        setSquads(Array.isArray(data) ? data : []);
                        setLoading(false);
                    })
                    .catch(err => {
                        console.error("Failed to fetch players", err);
                        setLoading(false);
                    });
            }
        });
    }, [params]);

    const [selectedTeam, setSelectedTeam] = useState<string>("all");

    const teams = useMemo(() => {
        const teamMap = new Map();
        squads.forEach(s => {
            if (s.sl_teams) {
                teamMap.set(s.sl_teams.id, s.sl_teams.name);
            }
        });
        return Array.from(teamMap.entries()).map(([id, name]) => ({ id, name }))
            .sort((a, b) => a.name.localeCompare(b.name));
    }, [squads]);

    const filteredSquads = useMemo(() => {
        let result = squads;

        if (selectedTeam !== "all") {
            result = result.filter(s => s.team_id === selectedTeam);
        }

        if (searchTerm.trim()) {
            const term = searchTerm.toLowerCase();
            result = result.filter(s =>
                s.sl_players?.name?.toLowerCase().includes(term) ||
                s.sl_teams?.name?.toLowerCase().includes(term)
            );
        }

        return result;
    }, [squads, searchTerm, selectedTeam]);

    if (!loading && !leagueInfo) {
        return (
            <div className="emptyState">
                <h2>리그를 찾을 수 없습니다</h2>
                <p>올바른 리그를 선택해주세요.</p>
            </div>
        );
    }

    return (
        <div className="playersContainer">
            <div className="pageHeader">
                <h1>{leagueInfo?.name} 선수진</h1>
                <p className="leagueInfo">
                    {leagueInfo?.sport} • {leagueInfo?.country}
                </p>
            </div>

            <div className="playersContent">
                <div className="searchSection filterWrapper">
                    <div className="searchContainer">
                        <select
                            className="textInput teamSelect"
                            value={selectedTeam}
                            onChange={(e) => setSelectedTeam(e.target.value)}
                        >
                            <option value="all">모든 팀</option>
                            {teams.map(team => (
                                <option key={team.id} value={team.id}>{team.name}</option>
                            ))}
                        </select>
                        <input
                            type="text"
                            placeholder="선수 또는 팀 이름으로 검색..."
                            className="searchInput"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <div className="gameCount">
                        {loading ? "불러오는 중..." : `총 ${filteredSquads.length}명의 선수`}
                    </div>
                </div>

                <div className="playersList">
                    {loading ? (
                        Array.from({ length: 8 }).map((_, i) => (
                            <div key={i} className="playerCard skeleton" style={{ opacity: 0.5 }}>
                                <div className="playerPhoto"></div>
                                <div className="playerInfo">
                                    <div style={{ height: '1.2rem', width: '60%', background: 'var(--border)', borderRadius: '4px' }}></div>
                                    <div style={{ height: '0.9rem', width: '40%', background: 'var(--border)', borderRadius: '4px' }}></div>
                                </div>
                            </div>
                        ))
                    ) : filteredSquads.length > 0 ? (
                        filteredSquads.map((squad) => {
                            const primaryName = squad.sl_players?.name?.trim();
                            const fallbackName = [squad.sl_players?.lastname, squad.sl_players?.firstname]
                                .filter(Boolean)
                                .join(" ");
                            const displayName = primaryName || fallbackName || "선수 이름";
                            const teamCode = squad.sl_teams?.code?.toUpperCase();
                            const teamName = squad.sl_teams?.name?.trim() || "";
                            const teamColor =
                                (teamCode ? teamColorMap[teamCode] : undefined) ||
                                teamNameColorMap[teamName];

                            return (
                                <Link
                                    key={squad.id}
                                    href={`/players/${leagueSlug}/${squad.player_id}`}
                                    className="playerCard"
                                >
                                    <div className="playerPhoto">
                                        <img
                                            src={squad.sl_players?.photo_url || "/images/noimage.png"}
                                            alt={squad.sl_players?.name || "Player Profile"}
                                            onError={(e) => {
                                                (e.target as HTMLImageElement).src = "/images/noimage.png";
                                                (e.target as HTMLImageElement).style.opacity = "0.5";
                                            }}
                                            style={!squad.sl_players?.photo_url ? { opacity: 0.5 } : {}}
                                        />
                                    </div>
                                    <div className="playerInfo">
                                    <div className="playerTopRow">
                                        <p className="playerTeam" style={teamColor ? { color: teamColor } : undefined}>
                                            {squad.sl_teams?.name || "소속팀"}
                                        </p>
                                        {squad.jersey_number !== null && (
                                            <span className="playerNumber">#{squad.jersey_number}</span>
                                        )}
                                    </div>
                                    <h3 className="playerName">{displayName}</h3>
                                </div>
                            </Link>
                        );
                    })
                    ) : (
                        <div className="emptyState">
                            <p>검색 결과가 없습니다.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

