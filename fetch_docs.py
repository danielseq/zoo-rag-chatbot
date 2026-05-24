import wikipediaapi
import os
from config import DOCS_DIR

wiki = wikipediaapi.Wikipedia(
    language='en',
    user_agent='zoo-rag-chatbot/1.0'
)

SPECIES = [
    "African elephant",
    "Tiger",
    "Mountain gorilla",
    "Giant panda",
    "Amur leopard",
    "Black rhinoceros",
    "Green sea turtle",
    "Snow leopard",
    "Vaquita",
    "African penguin",
    "West Indian manatee",
    "Polar bear",
    "Chimpanzee",
    "Whale shark",
    "Sumatran orangutan",
]

def fetch_and_save(species_name):
    print(f"Fetching: {species_name}...")
    page = wiki.page(species_name)
    
    if not page.exists():
        print(f"  Page not found: {species_name}")
        return
        
    filename = species_name.lower().replace(" ", "_") + ".md"
    filepath = os.path.join(DOCS_DIR, filename)
    content = f"# {page.title}\n\n{page.text}"
    
    with open(filepath, "w") as f:
        f.write(content)
    print(f"  Saved {filename} ({len(page.text)} chars)")

def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    for species in SPECIES:
        fetch_and_save(species)
    print("\nDone! Docs saved to", DOCS_DIR)

if __name__ == "__main__":
    main()