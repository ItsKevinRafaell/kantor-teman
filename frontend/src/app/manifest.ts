import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Kantor Teman",
    short_name: "KantorTeman",
    description: "CRM internal untuk prospek bisnis lokal",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#fcfaf7",
    theme_color: "#f5a700",
    orientation: "portrait",
    icons: [
      { src: "/icons/icon-72x72.png",   sizes: "72x72",   type: "image/png" },
      { src: "/icons/icon-96x96.png",   sizes: "96x96",   type: "image/png" },
      { src: "/icons/icon-128x128.png", sizes: "128x128", type: "image/png" },
      { src: "/icons/icon-144x144.png", sizes: "144x144", type: "image/png" },
      { src: "/icons/icon-152x152.png", sizes: "152x152", type: "image/png" },
      { src: "/icons/icon-192x192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-384x384.png", sizes: "384x384", type: "image/png" },
      { src: "/icons/icon-512x512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
