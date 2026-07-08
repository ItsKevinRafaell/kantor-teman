"use client";

import { useEffect, useState } from "react";

export type LogoVariant = "primary" | "secondary" | "icon";
export type LogoColor = "yellow" | "white";
export type LogoSize = "favicon" | "sm" | "md" | "lg" | "xl" | number;

interface LogoProps {
  /** Logo shape: primary lockup, secondary lockup, or just the brandmark icon */
  variant?: LogoVariant;
  /** Logo colour: yellow (default) shows on light bg; white for dark bg */
  color?: LogoColor;
  /** Render size. Number = explicit width in px; otherwise semantic sizes. */
  size?: LogoSize;
  /** Override the static master path. Use this for the dynamic Brand-Kit
   *  asset URL (admin-uploaded file). */
  src?: string;
  className?: string;
  alt?: string;
  /** Override the public-path of the static fall-back image. */
  fallbackSrc?: string;
}

const STATIC_BASE: Record<LogoVariant, Record<LogoColor, string>> = {
  primary: {
    yellow: "/brand/master/primary-yellow.png",
    white:  "/brand/master/primary-white.png",
  },
  secondary: {
    yellow: "/brand/master/secondary-yellow.png",
    white:  "/brand/master/secondary-white.png",
  },
  icon: {
    yellow: "/brand/master/icon-yellow.png",
    white:  "/brand/master/icon-white.png",
  },
};

const DEFAULT_SIZE_PX: Record<string, number> = {
  favicon: 24,
  sm: 32,
  md: 64,
  lg: 96,
  xl: 160,
};

/**
 * Single source of truth for the Teman UMKM Kita brand mark.
 *
 *   <Logo />                           — 64px primary yellow
 *   <Logo variant="icon" size={32} />  — 32px icon
 *   <Logo color="white" />             — primary white for dark backgrounds
 *   <Logo src={kit.logo_url} />        — admin-uploaded dynamic logo
 */
export default function Logo({
  variant = "primary",
  color = "yellow",
  size = "md",
  src,
  className,
  alt = "Teman UMKM Kita",
  fallbackSrc,
}: LogoProps) {
  const staticSrc = fallbackSrc ?? STATIC_BASE[variant][color];
  const finalSrc = src ?? staticSrc;

  const heightPx = typeof size === "number" ? size : DEFAULT_SIZE_PX[size];
  // Primary/secondary lockups are 2:1, icon is 1:1. Use intrinsic aspect
  // ratio by leaving width off and using height only.
  return (
    /* eslint-disable-next-line @next/next/no-img-element */
    <img
      src={finalSrc}
      alt={alt}
      height={heightPx}
      width={variant === "icon" ? heightPx : heightPx * 2}
      className={className}
      loading="eager"
      decoding="async"
    />
  );
}

/**
 * Hook variant — pulls the admin-uploaded default logo from the Brand Kit
 * public endpoint. Returns `{ logoUrl, logoColor }` once loaded.
 */
export function useBrandLogo(): { logoUrl: string | null; logoColor: LogoColor } {
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [logoColor, setLogoColor] = useState<LogoColor>("yellow");
  useEffect(() => {
    fetch("/api/brand-kit/public")
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (!data?.assets) return;
        const defId: string | undefined = data.default_document_asset_id;
        const def = defId ? data.assets.find((a: { id: string }) => a.id === defId) : null;
        const asset = def ?? data.assets.find((a: { asset_type: string }) =>
          ["logo_primary_yellow", "logo_primary", "logo_secondary", "brandmark"].includes(a.asset_type),
        );
        if (asset?.file_url) {
          const base = process.env.NEXT_PUBLIC_API_URL ?? "";
          setLogoUrl(`${base}${asset.file_url}`);
          if (asset.asset_type.endsWith("_white")) setLogoColor("white");
        }
      })
      .catch(() => {});
  }, []);
  return { logoUrl, logoColor };
}
