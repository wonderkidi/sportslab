import Link from "next/link";
import { LEAGUES } from "../config/leagues";

export default function ScheduleIndexPage() {
    return (
        <div className="leagueSelectionContainer">
            <div className="pageHeader">
                <h1>경기일정</h1>
                <p>리그를 선택하여 경기 일정을 확인하세요</p>
            </div>

            <div className="leagueGrid">
                {LEAGUES.map((league) => (
                    <Link
                        key={league.slug}
                        href={`/schedule/${league.slug}`}
                        className="leagueCard"
                    >
                        <div className="leagueCardHeader">
                            <h2>{league.name}</h2>
                            <span className="sportBadge">{league.sport}</span>
                        </div>
                        <p className="leagueCountry">{league.country}</p>
                        <div className="leagueCardFooter">
                            <span className="viewLink">일정 보기 →</span>
                        </div>
                    </Link>
                ))}
            </div>
        </div>
    );
}
