type UnderConstructionCardProps = {
  title: string;
  highlight?: string;
  detail?: string;
  badge?: string;
};

export default function UnderConstructionCard({
  title,
  highlight,
  detail,
  badge = "준비중",
}: UnderConstructionCardProps) {
  return (
    <article className="card cardLink">
      <div className="cardHeader">
        <h2 className="cardTitle">{title}</h2>
        <span className="cardBadge">{badge}</span>
      </div>
      <div className="cardBody">
        <p className="cardHighlight">{highlight ?? "데이터 준비중"}</p>
        <p className="cardDetail">
          {detail ?? "더 정확한 데이터를 제공하기 위해 준비하고 있습니다."}
        </p>
      </div>
    </article>
  );
}
