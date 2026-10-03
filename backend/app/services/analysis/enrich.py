from app.schemas.analysis import Analysis


def build_enrichment(
    analysis: Analysis,
    price: float | None,
    corroboration_count: int,
    macro_window: bool = False,
) -> dict:
    return {
        "price": price,
        "corroboration_count": corroboration_count,
        "macro_window": macro_window,
        "asset_resolved": bool(analysis.coins),
    }
