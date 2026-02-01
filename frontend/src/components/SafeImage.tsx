"use client";

import { CSSProperties, useEffect, useState } from "react";

type SafeImageProps = {
  src?: string | null;
  alt: string;
  fallbackSrc?: string;
  className?: string;
  style?: CSSProperties;
};

export default function SafeImage({
  src,
  alt,
  fallbackSrc = "/images/noimage.png",
  className,
  style,
}: SafeImageProps) {
  const [currentSrc, setCurrentSrc] = useState(src || fallbackSrc);

  useEffect(() => {
    setCurrentSrc(src || fallbackSrc);
  }, [src, fallbackSrc]);

  return (
    <img
      src={currentSrc}
      alt={alt}
      className={className}
      style={style}
      onError={() => setCurrentSrc(fallbackSrc)}
    />
  );
}
