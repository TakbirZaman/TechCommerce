#!/usr/bin/env python3
"""
One-off backfill: populate ProductSpecification.numeric_value from the
value string wherever numeric_value IS NULL.

Uses the shared unit-aware parser in core.services.ai_search
(parse_spec_number): Hz keys store Hz, size keys store inches,
GB/TB keys store GB (TB converted x1024). Values whose unit is missing
or incompatible with the key's family are skipped, never converted across
incompatible units.

Idempotent: only rows with numeric_value IS NULL are scanned, so a
re-run reports 0 backfilled rows.

Usage:
    python scripts/backfill_numeric_specs.py [--dry-run]

DATABASE_URL is honored (defaults to sqlite:///./techcommerce.db).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core.models.catalog  # noqa: F401,E402  (resolves Category relationship)
from core.database import SessionLocal  # noqa: E402
from core.models.specification import ProductSpecification  # noqa: E402
from core.services.ai_search import DB_SPEC_KEY_UNIT_FAMILY, parse_spec_number  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill numeric_value from spec value strings.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and report without committing any changes.")
    args = parser.parse_args()

    session = SessionLocal()
    # key -> [scanned, backfilled, skipped]
    summary: dict[str, list[int]] = {}
    other_scanned = other_skipped = 0
    try:
        known_keys = sorted(DB_SPEC_KEY_UNIT_FAMILY)
        rows = (
            session.query(ProductSpecification)
            .filter(ProductSpecification.numeric_value.is_(None),
                    ProductSpecification.spec_key.in_(known_keys))
            .all()
        )
        for row in rows:
            stats = summary.setdefault(row.spec_key, [0, 0, 0])
            stats[0] += 1
            parsed = parse_spec_number(row.spec_key, row.value)
            if parsed is None:
                stats[2] += 1
                continue
            row.numeric_value = float(parsed)
            stats[1] += 1

        if not args.dry_run:
            session.commit()
        else:
            session.rollback()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"{'spec_key':<22}{'scanned':>9}{'backfilled':>12}{'skipped':>9}")
    print("-" * 52)
    tot_scanned = tot_backfilled = tot_skipped = 0
    for key, (scanned, backfilled, skipped) in sorted(summary.items(),
                                                      key=lambda kv: (-kv[1][1], kv[0])):
        print(f"{key:<22}{scanned:>9}{backfilled:>12}{skipped:>9}")
        tot_scanned += scanned
        tot_backfilled += backfilled
        tot_skipped += skipped
    print("-" * 52)
    print(f"{'TOTAL':<22}{tot_scanned:>9}{tot_backfilled:>12}{tot_skipped:>9}")

    # rows under spec keys with no known unit family were not scanned at all
    other_scanned, other_skipped = _count_other_keys(session)
    if other_scanned:
        print(f"\nNot scanned ({other_scanned} rows under other spec keys, "
              f"no unit family - left as-is: {other_skipped} NULL numeric_value).")
    mode = "DRY-RUN (nothing committed)" if args.dry_run else "committed"
    print(f"\nDone [{mode}].")
    return 0


def _count_other_keys(session) -> tuple[int, int]:
    """Rows under spec keys outside the unit-family map (informational)."""
    known = list(DB_SPEC_KEY_UNIT_FAMILY)
    total = (
        session.query(ProductSpecification)
        .filter(ProductSpecification.numeric_value.is_(None),
                ~ProductSpecification.spec_key.in_(known))
        .count()
    )
    return total, total  # all of them remain NULL by design


if __name__ == "__main__":
    raise SystemExit(main())
