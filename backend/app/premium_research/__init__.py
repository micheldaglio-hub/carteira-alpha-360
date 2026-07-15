"""Alpha Premium Research package.

This package contains contracts and future services for the premium research,
publisher and subscription vertical. It must not contain UI logic.
"""
from app.premium_research.publisher import (
    build_publication_readiness_report,
    create_premium_research_draft,
    publication_to_dict,
)
from app.premium_research.performance_attribution import (
    attribution_run_to_dict,
    run_performance_attribution_for_publication,
)
from app.premium_research.entitlements import (
    authorize_premium_artifact_access,
    grant_subscription_to_user,
    inspect_premium_artifact_access,
    list_user_premium_access,
    seed_default_subscription_plans,
)
from app.premium_research.pdf_publisher import (
    render_pdf_from_html_artifact,
)
from app.premium_research.rating_engine import (
    rate_thesis_version,
    rating_to_dict,
    rating_version_to_dict,
    sync_ratings_for_publication,
    sync_ratings_from_thesis_versions,
)
from app.premium_research.research_committee import (
    committee_run_to_dict,
    run_research_committee,
    run_research_committee_for_publication,
)
from app.premium_research.renderer import (
    artifact_to_dict,
    render_publication_snapshot,
)
from app.premium_research.thesis_engine import (
    sync_theses_from_recommended_report,
    thesis_to_dict,
    thesis_version_to_dict,
    upsert_asset_thesis,
)

__all__ = [
    "build_publication_readiness_report",
    "create_premium_research_draft",
    "publication_to_dict",
    "attribution_run_to_dict",
    "run_performance_attribution_for_publication",
    "authorize_premium_artifact_access",
    "grant_subscription_to_user",
    "inspect_premium_artifact_access",
    "list_user_premium_access",
    "seed_default_subscription_plans",
    "render_pdf_from_html_artifact",
    "rate_thesis_version",
    "rating_to_dict",
    "rating_version_to_dict",
    "committee_run_to_dict",
    "run_research_committee",
    "run_research_committee_for_publication",
    "artifact_to_dict",
    "render_publication_snapshot",
    "sync_ratings_for_publication",
    "sync_ratings_from_thesis_versions",
    "sync_theses_from_recommended_report",
    "thesis_to_dict",
    "thesis_version_to_dict",
    "upsert_asset_thesis",
]
