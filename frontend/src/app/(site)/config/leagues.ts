export interface League {
  name: string;
  slug: string;
  sport: "baseball" | "basketball" | "soccer" | "football" | "hockey" | "cricket";
  country?: string;
}

export const LEAGUES: League[] = [
  { name: "KBO", slug: "kbo", sport: "baseball", country: "South Korea" },
  { name: "MLB", slug: "mlb", sport: "baseball", country: "USA" },
  { name: "NBA", slug: "nba", sport: "basketball", country: "USA" },
  { name: "EPL", slug: "epl", sport: "soccer", country: "England" },
  { name: "NFL", slug: "nfl", sport: "football", country: "USA" },
  { name: "NHL", slug: "nhl", sport: "hockey", country: "USA/Canada" },
  { name: "UCL", slug: "ucl", sport: "soccer", country: "Europe" },
  { name: "IPL", slug: "ipl", sport: "cricket", country: "India" },
  { name: "K-LEAGUE", slug: "k-league", sport: "soccer", country: "South Korea" },
  { name: "SERIE A", slug: "serie-a", sport: "soccer", country: "Italy" },
  { name: "LA LIGA", slug: "la-liga", sport: "soccer", country: "Spain" },
  { name: "BUNDESLIGA", slug: "bundesliga", sport: "soccer", country: "Germany" },
  { name: "KBL", slug: "kbl", sport: "basketball", country: "South Korea" },
];

// Legacy export for backward compatibility
export const LEAGUE_NAMES = LEAGUES.map(l => l.name);
