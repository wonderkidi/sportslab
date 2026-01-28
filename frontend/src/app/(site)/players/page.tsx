export default function PlayersPage() {
  return (
    <div className="playersWrap">
      <h4 className="titPage">선수 조회</h4>

      <div className="playersFilters">
        <select className="selectInput" defaultValue="">
          <option value="">팀 선택</option>
          <option value="LG">LG</option>
          <option value="HH">한화</option>
          <option value="SK">SSG</option>
          <option value="SS">삼성</option>
          <option value="NC">NC</option>
          <option value="KT">KT</option>
          <option value="LT">롯데</option>
          <option value="HT">KIA</option>
          <option value="OB">두산</option>
          <option value="WO">키움</option>
        </select>
        <select className="selectInput" defaultValue="">
          <option value="">포지션 선택</option>
          <option value="1">투수</option>
          <option value="2">포수</option>
          <option value="3,4,5,6">내야수</option>
          <option value="7,8,9">외야수</option>
        </select>
        <input className="textInput" type="text" placeholder="선수명 검색" />
        <button type="button" className="primaryBtn">
          검색
        </button>
      </div>

      <div className="playersResult">
        <p className="resultTitle">
          검색결과 : <span className="resultPoint">0</span>건
        </p>
        <div className="tableWrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>등번호</th>
                <th>선수명</th>
                <th>팀명</th>
                <th>포지션</th>
                <th>생년월일</th>
                <th>체격</th>
                <th>출신교</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>1</td>
                <td>
                  <a className="playerLink" href="/players/53455">
                    이호성
                  </a>
                </td>
                <td>삼성</td>
                <td>투수</td>
                <td>2004-08-14</td>
                <td>184cm/87kg</td>
                <td>인천고</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="paging">
          <button type="button" className="pageBtn isActive">
            1
          </button>
        </div>
      </div>
    </div>
  );
}
