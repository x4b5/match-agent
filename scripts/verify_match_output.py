import asyncio
import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.getcwd())

from backend.services.agents import match_kandidaat
from backend.services.llm_instance import init_provider
from backend.config import OLLAMA_MODEL

async def main():
    print(f"Initializing LLM provider for model: {OLLAMA_MODEL}")
    init_provider()
    
    cv_tekst = """
    Jan de Vries is een ervaren timmerman. Hij heeft 10 jaar gewerkt bij Bouwbedrijf Klaas. 
    Hij is een echte aanpakker, werkt graag in een team en is nuchter. 
    Hij wil graag meer leren over duurzaam bouwen.
    """
    
    vacature_tekst = """
    Gezocht: Allround Timmerman voor renovatieprojecten in Amsterdam.
    Wij zoeken iemand die van aanpakken weet en goed kan samenwerken in een klein team.
    Harde eis: 5 jaar ervaring als timmerman. 
    Wij bieden een gezellige werksfeer en ontwikkelingsmogelijkheden.
    """
    
    print("\nRunning Quick Scan Match...")
    try:
        result = await match_kandidaat(cv_tekst, vacature_tekst, modus="quick_scan")
        print("\nQuick Scan Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Basic validation
        assert "succes_plan" in result, "Succesplan missing from Quick Scan!"
        assert "actie_kandidaat" in result["succes_plan"], "actie_kandidaat missing!"
        assert len(result["matchende_punten"]) <= 3, "Too many match points!"
        
        print("\nVerification successful: Match contains Succesplan and follows new constraints.")
        
    except Exception as e:
        print(f"\nVerification failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
