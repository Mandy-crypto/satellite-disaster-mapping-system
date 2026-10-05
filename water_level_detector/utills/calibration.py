"""Calibration helpers for converting detected image pixels into water depth."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LevelCalibration:
    """Linear reference calibration: configured pixel span maps to known depth."""

    reference_height_cm: float
    reference_pixels: float
    zero_offset_cm: float = 0.0
    invert: bool = False

    def __post_init__(self):
        if self.reference_height_cm <= 0 or self.reference_pixels <= 0:
            raise ValueError("Reference height and pixel span must be positive")

    @property
    def centimeters_per_pixel(self) -> float:
        return self.reference_height_cm / self.reference_pixels

    def to_centimeters(self, pixels: float) -> float:
        pixels = float(pixels)
        if pixels < 0:
            raise ValueError("Pixel measurement cannot be negative")
        signed = -pixels if self.invert else pixels
        return max(0.0, self.zero_offset_cm + signed * self.centimeters_per_pixel)

    @classmethod
    def from_settings(cls, path: str | Path | None = None) -> "LevelCalibration":
        settings_path = Path(path) if path else Path(__file__).resolve().parents[1] / "config" / "settings.json"
        with settings_path.open(encoding="utf-8") as settings_file:
            data = json.load(settings_file).get("calibration", {})
        return cls(**data)

    def save(self, path: str | Path | None = None) -> Path:
        settings_path = Path(path) if path else Path(__file__).resolve().parents[1] / "config" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with settings_path.open(encoding="utf-8") as settings_file:
            data = json.load(settings_file)
        data["calibration"] = {
            "reference_height_cm": self.reference_height_cm,
            "reference_pixels": self.reference_pixels,
            "zero_offset_cm": self.zero_offset_cm,
            "invert": self.invert,
        }
        temporary = settings_path.with_suffix(settings_path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        temporary.replace(settings_path)
        return settings_path


def main():
    parser = argparse.ArgumentParser(description="Set the pixel-to-centimeter water gauge calibration")
    parser.add_argument("--height-cm", type=float, required=True, help="Known physical height represented by the pixel span")
    parser.add_argument("--pixels", type=float, required=True, help="Measured pixel span corresponding to --height-cm")
    parser.add_argument("--zero-offset-cm", type=float, default=0.0)
    parser.add_argument("--invert", action="store_true", help="Invert the level direction")
    parser.add_argument("--settings", help="Settings JSON path; defaults to config/settings.json")
    args = parser.parse_args()
    calibration = LevelCalibration(args.height_cm, args.pixels, args.zero_offset_cm, args.invert)
    path = calibration.save(args.settings)
    print(f"Saved calibration to {path} ({calibration.centimeters_per_pixel:.4f} cm/pixel)")


if __name__ == "__main__":
    main()
