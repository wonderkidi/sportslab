import Link from "next/link";

type DetailPageProps = {
  params: { league: string };
};

export default function DetailPage({ params }: DetailPageProps) {
  const league = (params?.league ?? "").replace(/-/g, " ").toUpperCase();

  return (
    <div id="contents" className="detailWrap">
      <div className="detailTop">
        <Link href="/" className="backIcon" aria-label="메인으로">
          back
        </Link>
      </div>

      <h4 className="titPage">경기일정・결과</h4>

      <div className="dateSelect">
        <ul className="date">
          <li className="prev">
            <button type="button" aria-label="이전">
              ‹
            </button>
          </li>
          <li className="dateSelectInner">
            <select id="ddlYear" defaultValue="2026">
              <option value="2026">2026</option>
              <option value="2025">2025</option>
              <option value="2024">2024</option>
            </select>
            <select id="ddlMonth" defaultValue="03">
              <option value="01">01</option>
              <option value="02">02</option>
              <option value="03">03</option>
              <option value="04">04</option>
            </select>
          </li>
          <li className="next">
            <button type="button" aria-label="다음">
              ›
            </button>
          </li>
        </ul>
        <div className="teamSelect">
          <select id="ddlTeam" defaultValue="ALL">
            <option value="ALL">전체</option>
            {["LG", "한화", "SSG", "삼성", "NC", "KT", "롯데", "KIA", "두산", "키움"].map(
              (team) => (
                <option key={team} value={team}>
                  {team}
                </option>
              )
            )}
          </select>
        </div>
      </div>

      <div id="boxList">
        <div className="tblType">
          <table className="tbl">
            <thead>
              <tr>
                <th>날짜</th>
                <th>시간</th>
                <th>경기</th>
                <th>게임센터</th>
                <th>하이라이트</th>
                <th>TV</th>
                <th>라디오</th>
                <th>구장</th>
                <th>비고</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="day">03.28(토)</td>
                <td className="time">
                  <b>14:00</b>
                </td>
                <td className="play">
                  <span>KT</span>
                  <em>vs</em>
                  <span>LG</span>
                </td>
                <td className="relay">-</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td>잠실</td>
                <td>-</td>
              </tr>
              <tr>
                <td className="day">03.29(일)</td>
                <td className="time">
                  <b>14:00</b>
                </td>
                <td className="play">
                  <span>KIA</span>
                  <em>vs</em>
                  <span>SSG</span>
                </td>
                <td className="relay">-</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td>문학</td>
                <td>-</td>
              </tr>
              <tr>
                <td className="day">03.31(화)</td>
                <td className="time">
                  <b>18:30</b>
                </td>
                <td className="play">
                  <span>롯데</span>
                  <em>vs</em>
                  <span>NC</span>
                </td>
                <td className="relay">-</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td>창원</td>
                <td>-</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div id="boxCal" className="boxCal">
        <table className="schedulCalender">
          <thead>
            <tr>
              <th scope="col">일</th>
              <th scope="col">월</th>
              <th scope="col">화</th>
              <th scope="col">수</th>
              <th scope="col">목</th>
              <th scope="col">금</th>
              <th scope="col">토</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              {Array.from({ length: 7 }, (_, i) => (
                <td key={i}>
                  <span className="dayNum">{i + 1}</span>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="detailEmpty">
        <span className="detailEmptyText">{league}</span>
      </div>
    </div>
  );
}
