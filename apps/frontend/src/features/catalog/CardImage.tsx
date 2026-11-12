import { useI18n } from "@/shared/i18n";
import { useState } from "react";
import { ImageOff } from "lucide-react";
import type { Card } from "./types";
export function CardImage({ card }: { card: Card }) {
  const { t } = useI18n();
  const [brokenUrl, setBrokenUrl] = useState<string>();
  return card.image_urls[0] && brokenUrl !== card.image_urls[0] ? (
    <img
      src={card.image_urls[0]}
      alt={card.name}
      loading="lazy"
      onError={() => setBrokenUrl(card.image_urls[0])}
    />
  ) : (
    <div className="image-missing">
      <ImageOff />
      <span>{t("Image indisponible")}</span>
    </div>
  );
}
