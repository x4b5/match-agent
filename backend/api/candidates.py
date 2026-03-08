"""Kandidaten router — dunne wrapper rond de generieke DocumentRouter."""
import backend.config
from backend.services.agents import profileer_kandidaat, verrijk_kandidaat_profiel
from backend.api.base_router import create_document_router

router = create_document_router(
    prefix="/candidates",
    tag="Kandidaten",
    get_base_dir=lambda: backend.config.KANDIDATEN_DIR,
    doc_type="kandidaat",
    profiel_agent_fn=profileer_kandidaat,
    verrijk_agent_fn=verrijk_kandidaat_profiel,
    auto_shortlist=False,
)
