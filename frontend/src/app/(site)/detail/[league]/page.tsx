import Link from "next/link";

type DetailPageProps = {
  params: { league: string };
};

export default function DetailPage({ params }: DetailPageProps) {
  const league = (params?.league ?? "unknown").replace(/-/g, " ").toUpperCase();

  return (
    <>
      <div className="detailTop">
        <Link href="/" className="backIcon" aria-label="메인으로">
          back
        </Link>
      </div>
      <article className="detailWide">
        <div className="detailEmpty">
          <span className="detailEmptyText">준비중</span>
        </div>
      </article>
    </>
  );
}
