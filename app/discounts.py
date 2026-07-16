"""Curated discount configs for the quote UI (D3, ruling 2026-07-16).

Demo fixture now; staging reads szempont.discount_configs (DDL v2) through
the same load_discount_configs() signature — the quote route never knows the
difference. Free-form discounts do not exist anywhere in Szempont.
"""
from decimal import Decimal as D

from quotes.records import DiscountConfig

DISCOUNT_CONFIGS: tuple[DiscountConfig, ...] = (
    DiscountConfig("TORZS10", "Törzsvásárlói 10%", "percent", D("10"),
                   valid_from="2026-01-01"),
    DiscountConfig("LENCSE15", "Lencseakció 15% (csak lencse)", "percent",
                   D("15"), applies_to_line_types=frozenset({"lens"}),
                   valid_from="2026-07-01", valid_to="2026-08-31"),
    DiscountConfig("DOLG25", "Dolgozói 25%", "percent", D("25"),
                   requires_approval=True, valid_from="2026-01-01"),
    DiscountConfig("KUPON5E", "Kupon 5 000 Ft", "amount_net", D("5000"),
                   valid_from="2026-07-01", valid_to="2026-09-30"),
)


def load_discount_configs() -> tuple[DiscountConfig, ...]:
    # TODO(staging): BQ-backed loader over szempont.discount_configs,
    # same return type, active/effective-dated rows only.
    return DISCOUNT_CONFIGS


def get_discount_config(config_id: str) -> DiscountConfig | None:
    return next((c for c in load_discount_configs()
                 if c.config_id == config_id), None)
