import Link from "next/link";

type PlayerPageProps = {
  params: { playerId: string };
};

export default function PlayerPage({ params }: PlayerPageProps) {
  const playerId = params?.playerId ?? "";

  return (
    <div className="playerDetailWrap">
      <div className="detailTop">
        <Link href="/players" className="backIcon" aria-label="선수 목록">
          back
        </Link>
      </div>

      <h4 className="titPage">선수 조회</h4>

      <section className="playerInfo">
        <div className="playerTeam">
          <div className="teamBadge">삼성 라이온즈</div>
          <div className="teamSub">PLAYER ID: {playerId}</div>
        </div>

        <div className="playerBasic">
          <div className="playerPhoto">PHOTO</div>
          <ul className="playerMeta">
            <li>
              <strong>선수명:</strong> <span>이호성</span>
            </li>
            <li>
              <strong>등번호:</strong> <span>No.1</span>
            </li>
            <li>
              <strong>생년월일:</strong> <span>2004년 08월 14일</span>
            </li>
            <li>
              <strong>포지션:</strong> <span>투수(우투우타)</span>
            </li>
            <li>
              <strong>신장/체중:</strong> <span>184cm/87kg</span>
            </li>
            <li>
              <strong>경력:</strong> <span>도원초-동인천중-인천고</span>
            </li>
            <li>
              <strong>입단 계약금:</strong> <span>20000만원</span>
            </li>
            <li>
              <strong>연봉:</strong> <span>4000만원</span>
            </li>
            <li>
              <strong>지명순위:</strong> <span>23 삼성 1라운드 8순위</span>
            </li>
            <li>
              <strong>입단년도:</strong> <span>23삼성</span>
            </li>
          </ul>
        </div>

        <div className="playerTabs">
          <div className="tabGroup">
            <button type="button" className="tabBtn">
              타자
            </button>
            <button type="button" className="tabBtn isActive">
              투수
            </button>
          </div>
          <div className="tabGroup">
            {["기본기록", "통산기록", "일자별기록", "경기별기록", "상황별기록", "등록일수"].map(
              (label) => (
                <button
                  key={label}
                  type="button"
                  className={`tabBtn ${label === "기본기록" ? "isActive" : ""}`}
                >
                  {label}
                </button>
              )
            )}
          </div>
        </div>
      </section>

      <section className="playerRecords">
        <h6 className="sectionTitle">2025 성적</h6>
        <div className="tableWrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>팀명</th>
                <th>ERA</th>
                <th>G</th>
                <th>W</th>
                <th>L</th>
                <th>SV</th>
                <th>HLD</th>
                <th>IP</th>
                <th>H</th>
                <th>HR</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>삼성</td>
                <td>6.34</td>
                <td>58</td>
                <td>7</td>
                <td>4</td>
                <td>9</td>
                <td>3</td>
                <td>55 1/3</td>
                <td>54</td>
                <td>7</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h6 className="sectionTitle">최근 10경기</h6>
        <div className="tableWrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>일자</th>
                <th>상대</th>
                <th>결과</th>
                <th>ERA</th>
                <th>IP</th>
                <th>H</th>
                <th>HR</th>
                <th>BB</th>
                <th>SO</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>09.26</td>
                <td>롯데</td>
                <td>-</td>
                <td>54.00</td>
                <td>1/3</td>
                <td>1</td>
                <td>0</td>
                <td>1</td>
                <td>1</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h6 className="sectionTitle">연도별 TOP 10</h6>
        <div className="tableWrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>연도</th>
                <th>항목</th>
                <th>기록</th>
                <th>순위</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colSpan={4} className="emptyRow">
                  기록이 없습니다.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
