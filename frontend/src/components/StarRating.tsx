"use client";

import { useState } from "react";
import { Star } from "lucide-react";
import { apiFetch } from "../lib/api";

interface StarRatingProps {
  leadId: number;
  value: number;
  onChange?: (newRating: number) => void;
}

export default function StarRating({ leadId, value, onChange }: StarRatingProps) {
  const [hovered, setHovered] = useState(0);
  const [current, setCurrent] = useState(value);
  const [saving, setSaving] = useState(false);

  async function handleClick(star: number) {
    if (saving) return;
    setSaving(true);
    try {
      const res = await apiFetch(`/api/leads/${leadId}/rating`, {
        method: "PATCH",
        body: JSON.stringify({ rating: star }),
      });
      if (res.ok) {
        setCurrent(star);
        onChange?.(star);
      }
    } catch {
      /* silent */
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex items-center gap-0.5" onMouseLeave={() => setHovered(0)}>
      {[1, 2, 3, 4, 5].map((star) => {
        const active = star <= (hovered || current);
        return (
          <button
            key={star}
            type="button"
            disabled={saving}
            onMouseEnter={() => setHovered(star)}
            onClick={() => handleClick(star)}
            className="p-0 border-0 bg-transparent cursor-pointer disabled:cursor-wait transition-transform hover:scale-110"
          >
            <Star
              size={16}
              className={active ? "text-amber-400 fill-amber-400" : "text-gray-300"}
            />
          </button>
        );
      })}
    </div>
  );
}
