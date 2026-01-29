# SportsLab - 스포츠 리그 페이지 구조

## 📁 페이지 구조

각 스포츠 리그별로 **경기일정**, **경기결과**, **선수조회** 페이지가 분리되어 있습니다.

### 메인 네비게이션
- `/` - 전체 대시보드
- `/schedule/[league]` - 특정 리그의 경기일정
- `/results/[league]` - 특정 리그의 경기결과
- `/players/[league]` - 특정 리그의 선수 목록
- `/players/[league]/[playerId]` - 특정 리그 선수의 상세 정보

## 🏆 지원 리그 목록

| 리그 이름 | Slug | 스포츠 | 국가 |
|----------|------|--------|------|
| KBO | `kbo` | Baseball | South Korea |
| MLB | `mlb` | Baseball | USA |
| NBA | `nba` | Basketball | USA |
| EPL | `epl` | Soccer | England |
| NFL | `nfl` | Football | USA |
| NHL | `nhl` | Hockey | USA/Canada |
| UCL | `ucl` | Soccer | Europe |
| IPL | `ipl` | Cricket | India |
| K-LEAGUE | `k-league` | Soccer | South Korea |
| SERIE A | `serie-a` | Soccer | Italy |
| LA LIGA | `la-liga` | Soccer | Spain |
| BUNDESLIGA | `bundesliga` | Soccer | Germany |
| KBL | `kbl` | Basketball | South Korea |

## 📄 파일 구조

```
src/app/(site)/
├── config/
│   └── leagues.ts          # 리그 설정 및 메타데이터
├── schedule/
│   ├── page.tsx            # 리그 선택 페이지
│   └── [league]/
│       └── page.tsx        # 리그별 경기일정
├── results/
│   ├── page.tsx            # 리그 선택 페이지
│   └── [league]/
│       └── page.tsx        # 리그별 경기결과
├── players/
│   ├── page.tsx            # 리그 선택 페이지
│   └── [league]/
│       ├── page.tsx        # 리그별 선수 조회
│       └── [playerId]/
│           └── page.tsx    # 선수 상세 정보
├── SiteShell.tsx           # 공통 레이아웃
└── layout.tsx              # 사이트 레이아웃
```

## 🎨 스타일링

- `common.css` - 기본 컴포넌트 스타일
- `league-pages.css` - 리그 페이지 전용 스타일
- `theme.css` - 테마 변수 및 색상

## 🔧 사용 방법

### 리그 추가하기

`src/app/(site)/config/leagues.ts` 파일에 새 리그를 추가:

```typescript
{
  name: "NEW LEAGUE",
  slug: "new-league",
  sport: "baseball" | "basketball" | "soccer" | "football" | "hockey" | "cricket",
  country: "Country Name"
}
```

### 페이지 커스터마이징

각 `[league]/page.tsx` 파일에서 리그별 데이터를 가져와 표시할 수 있습니다:

```typescript
const league = LEAGUES.find((l) => l.slug === leagueSlug);
// 리그 정보를 사용하여 API 호출 또는 데이터 표시
```

## 🚀 다음 단계

1. **데이터 연동**: 각 페이지에 실제 API 데이터 연결
2. **필터링**: 날짜, 팀, 포지션별 필터 기능 구현
3. **상세 페이지**: 경기 상세, 선수 상세 페이지 추가
4. **실시간 업데이트**: 경기 중 실시간 스코어 업데이트
