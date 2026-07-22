"""Drive an MPC order from a manifest. Dry-run works with no browser deps."""

from __future__ import annotations

from pathlib import Path

from .plan import (
    MPC_MAX_CARDS_PER_PROJECT,
    UploadPlan,
    load_manifest,
    plan_from_manifest,
)


def run(manifest_path: Path, dry_run: bool = True, headed: bool = True,
        preview: int = 12) -> int:
    manifest = load_manifest(manifest_path)
    plan = plan_from_manifest(manifest, root=manifest_path.resolve().parent
                              if not manifest.get("root") else None)
    print_plan(plan, preview=preview)

    if plan.exceeds_project_limit:
        print(f"\n! {plan.total_cards} cards exceeds one MPC project "
              f"(max {MPC_MAX_CARDS_PER_PROJECT}). Split into multiple orders.")

    if dry_run:
        print("\nDry run: no browser launched. "
              "Re-run without --dry-run to drive MakePlayingCards.")
        return 0

    try:
        from .driver import MpcDriver  # noqa: F401  (lazy: needs playwright)
    except ImportError as exc:
        print(f"\nBrowser automation unavailable: {exc}\n"
              "Install it with:  pip install -e .[upload] && playwright install chromium")
        return 3

    driver = MpcDriver(headed=headed)
    return driver.fill_order(plan)


def print_plan(plan: UploadPlan, preview: int = 12) -> None:
    print(f"Total cards (slots) : {plan.total_cards}")
    print(f"Unique front images : {len(plan.unique_fronts)}")
    print(f"Unique back images  : {len(plan.unique_backs)}")

    if plan.missing_files:
        print(f"\n! Missing {len(plan.missing_files)} image file(s):")
        for p in plan.missing_files[:20]:
            print(f"  - {p}")

    print(f"\nFirst {min(preview, plan.total_cards)} slots:")
    for i, slot in enumerate(plan.slots[:preview], 1):
        back = slot.back.name if slot.back else "(no back)"
        print(f"  {i:>3}. [{slot.category:<9}] {slot.front.name}  <->  {back}")
