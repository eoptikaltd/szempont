"""Lens thickness estimation — the consultation-screen demo math.

Geometry-based sag approximation (industry-standard estimate, same class as
public thickness calculators): sag(r) = (|D| * r^2) / (2000 * (n - 1)).
Minus lens: edge = center_min + sag at effective radius.
Plus lens:  center = edge_min + sag.
Effective radius accounts for frame effective diameter and PD decentration
(frame PD vs wearer PD pushes the optical center, adding material on one side).

This is an ESTIMATE for comparative visualization ("becsült érték") — the real
figure comes from the supplier's calculation at order time. Honest by design:
the visual compares indices/frames, it does not promise millimetres.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ThicknessEstimate:
    index: Decimal
    edge_mm: Decimal      # minus lens dominant figure
    center_mm: Decimal
    weight_factor: Decimal  # relative to 1.50 baseline, same geometry


def _sag_mm(power_abs: Decimal, radius_mm: Decimal, index: Decimal) -> Decimal:
    return (power_abs * radius_mm * radius_mm) / (Decimal(2000) * (index - 1))


def estimate_thickness(
    sph: Decimal,
    cyl: Decimal,
    index: Decimal,
    frame_ed_mm: Decimal = Decimal("50"),
    decentration_mm: Decimal = Decimal("2"),
    center_min_mm: Decimal = Decimal("1.8"),
    edge_min_mm: Decimal = Decimal("1.0"),
) -> ThicknessEstimate:
    """Worst-meridian estimate: for minus cyl, the strongest meridian is
    sph + cyl (both negative conventions); that meridian sets max edge."""
    strongest = sph + cyl if (sph <= 0 and cyl <= 0) else sph
    power_abs = abs(strongest)
    r = frame_ed_mm / 2 + decentration_mm
    sag = _sag_mm(power_abs, r, index)

    if strongest < 0:
        edge = center_min_mm + sag
        center = center_min_mm
    else:
        center = edge_min_mm + sag
        edge = edge_min_mm

    # density ratios vs CR-39 baseline (approx: 1.50=1.32, 1.60=1.30,
    # 1.67=1.35, 1.74=1.46 g/cm3) combined with volume reduction via sag ratio
    density = {
        Decimal("1.50"): Decimal("1.32"), Decimal("1.56"): Decimal("1.28"),
        Decimal("1.60"): Decimal("1.30"), Decimal("1.67"): Decimal("1.35"),
        Decimal("1.74"): Decimal("1.46"),
    }.get(index, Decimal("1.32"))
    base_sag = _sag_mm(power_abs, r, Decimal("1.50"))
    vol_ratio = (sag / base_sag) if base_sag else Decimal(1)
    weight = (vol_ratio * density / Decimal("1.32")).quantize(Decimal("0.01"))

    q = Decimal("0.1")
    return ThicknessEstimate(
        index=index,
        edge_mm=edge.quantize(q),
        center_mm=center.quantize(q),
        weight_factor=weight,
    )


def compare_indices(sph: Decimal, cyl: Decimal, frame_ed_mm: Decimal,
                    indices=(Decimal("1.50"), Decimal("1.56"), Decimal("1.60"),
                             Decimal("1.67"), Decimal("1.74"))) -> list[ThicknessEstimate]:
    return [estimate_thickness(sph, cyl, i, frame_ed_mm) for i in indices]
