import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from backend.services.agents import profileer_kandidaat, profileer_werkgeversvraag

async def main():
    print("Testing Candidate Profiling...")
    cand_text = "Jan Jansen is een ervaren timmerman uit Haarlem."
    cand_profile = await profileer_kandidaat(cand_text)
    print("Candidate Questions:", cand_profile.get("vervolgvragen", []))
    
    print("\nTesting Employer Profiling...")
    empl_text = "Gezocht: Timmerman in Amsterdam. We zijn een gezellig team."
    empl_profile = await profileer_werkgeversvraag(empl_text)
    print("Employer Questions:", empl_profile.get("vervolgvragen", []))

if __name__ == "__main__":
    asyncio.run(main())
