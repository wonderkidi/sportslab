import type { Metadata } from "next";
import localFont from "next/font/local";
import "./theme.css";
import "./common.css";
import "./league-pages.css";
import "./globals.css";

const displayFont = localFont({
  variable: "--font-display",
  src: [
    {
      path: "../../public/fonts/KBO-Dia-Gothic_light.woff",
      weight: "300",
      style: "normal",
    },
    {
      path: "../../public/fonts/KBO-Dia-Gothic_medium.woff",
      weight: "500",
      style: "normal",
    },
    {
      path: "../../public/fonts/KBO-Dia-Gothic_bold.woff",
      weight: "700",
      style: "normal",
    },
  ],
  display: "swap",
});

const bodyFont = localFont({
  variable: "--font-body",
  src: [
    {
      path: "../../public/fonts/KBO-Dia-Gothic_light.woff",
      weight: "300",
      style: "normal",
    },
    {
      path: "../../public/fonts/KBO-Dia-Gothic_medium.woff",
      weight: "500",
      style: "normal",
    },
    {
      path: "../../public/fonts/KBO-Dia-Gothic_bold.woff",
      weight: "700",
      style: "normal",
    },
  ],
  display: "swap",
});

export const metadata: Metadata = {
  title: "SportsLab",
  description: "MLB, NBA, NFL, EPL, NHL, UCL 경기결과 대시보드",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" data-theme="dark">
      <body className={`${displayFont.variable} ${bodyFont.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
