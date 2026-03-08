"""Werkgevers router — dunne wrapper rond de generieke DocumentRouter."""
import backend.config
from backend.services.agents import profileer_werkgeversvraag, verrijk_werkgeversvraag_profiel
from backend.api.base_router import create_document_router

router = create_document_router(
    prefix="/employers",
    tag="Werkgevers",
    get_base_dir=lambda: backend.config.WERKGEVERSVRAGEN_DIR,
    doc_type="vacature",
    profiel_agent_fn=profileer_werkgeversvraag,
    verrijk_agent_fn=verrijk_werkgeversvraag_profiel,
    auto_shortlist=True,
)
