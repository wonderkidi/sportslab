import { PropsWithChildren } from "react";
import SiteShell from "./SiteShell";

export default function SiteLayout({ children }: PropsWithChildren) {
  return <SiteShell>{children}</SiteShell>;
}
