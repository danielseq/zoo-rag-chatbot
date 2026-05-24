import requests
import os
import time
from config import IUCN_API_KEY, IUCN_BASE_URL, DOCS_DIR

SPECIES = [
    "Loxodonta africana",       # African Elephant
    "Panthera tigris",          # Tiger
    "Gorilla beringei",         # Mountain Gorilla
    "Ailuropoda melanoleuca",   # Giant Panda
    "Panthera pardus orientalis", # Amur Leopard
    "Diceros bicornis",         # Black Rhino
    "Chelonia mydas",           # Green Sea Turtle
    "Panthera uncia",           # Snow Leopard
    "Phocoena sinus",           # Vaquita
    "Spheniscus demersus",      # African Penguin
    "Gorilla gorilla",          # Western Gorilla
    "Trichechus manatus",       # West Indian Manatee
    "Ursus maritimus",          # Polar Bear
    "Pan troglodytes",          # Chimpanzee
    "Rhincodon typus",          # Whale Shark
]

def fetch_species_data(scientific_name):
    name_encoded = scientific_name.replace(" ", "%20")
    
    # Get species info
    info_url = f"{IUCN_BASE_URL}/species/{name_encoded}?token={IUCN_API_KEY}"
    info_resp = requests.get(info_url)
    info_data = info_resp.json()
    
    if not info_data.get("result"):
        print(f"  No result for {scientific_name}")
        return None
    
    species = info_data["result"][0]
    
    # Get narrative (habitat, threats, conservation)
    narrative_url = f"{IUCN_BASE_URL}/species/narrative/{name_encoded}?token={IUCN_API_KEY}"
    narrative_resp = requests.get(narrative_url)
    narrative_data = narrative_resp.json()
    narrative = narrative_data.get("result", [{}])[0] if narrative_data.get("result") else {}
    
    # Get threats
    threats_url = f"{IUCN_BASE_URL}/threats/species/name/{name_encoded}?token={IUCN_API_KEY}"
    threats_resp = requests.get(threats_url)
    threats_data = threats_resp.json()
    threats = threats_data.get("result", [])
    
    # Get conservation measures
    measures_url = f"{IUCN_BASE_URL}/conservationmeasures/species/name/{name_encoded}?token={IUCN_API_KEY}"
    measures_resp = requests.get(measures_url)
    measures_data = measures_resp.json()
    measures = measures_data.get("result", [])
    
    return {
        "species": species,
        "narrative": narrative,
        "threats": threats,
        "measures": measures
    }

def build_markdown(data, scientific_name):
    s = data["species"]
    n = data["narrative"]
    threats = data["threats"]
    measures = data["measures"]
    
    common_name = s.get("main_common_name", "Unknown")
    category = s.get("category", "Unknown")
    
    category_labels = {
        "EX": "Extinct", "EW": "Extinct in the Wild",
        "CR": "Critically Endangered", "EN": "Endangered",
        "VU": "Vulnerable", "NT": "Near Threatened",
        "LC": "Least Concern", "DD": "Data Deficient"
    }
    status = category_labels.get(category, category)

    lines = [
        f"# {common_name} ({scientific_name})",
        f"\n## Conservation Status\n{status} ({category}) on the IUCN Red List",
        f"\n## Taxonomy",
        f"- **Class:** {s.get('class_name', 'N/A')}",
        f"- **Order:** {s.get('order_name', 'N/A')}",
        f"- **Family:** {s.get('family_name', 'N/A')}",
    ]

    if n.get("habitat"):
        lines.append(f"\n## Habitat\n{n['habitat']}")
    
    if n.get("population"):
        lines.append(f"\n## Population\n{n['population']}")

    if n.get("threats"):
        lines.append(f"\n## Threats\n{n['threats']}")
    elif threats:
        lines.append("\n## Threats")
        for t in threats[:5]:
            lines.append(f"- {t.get('title', '')}")

    if n.get("conservationmeasures"):
        lines.append(f"\n## Conservation Measures\n{n['conservationmeasures']}")
    elif measures:
        lines.append("\n## Conservation Measures")
        for m in measures[:5]:
            lines.append(f"- {m.get('title', '')}")

    if n.get("usetrade"):
        lines.append(f"\n## Use & Trade\n{n['usetrade']}")

    return "\n".join(lines)

def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    for scientific_name in SPECIES:
        print(f"Fetching {scientific_name}...")
        try:
            data = fetch_species_data(scientific_name)
            if data:
                md = build_markdown(data, scientific_name)
                filename = scientific_name.replace(" ", "_").lower() + ".md"
                filepath = os.path.join(DOCS_DIR, filename)
                with open(filepath, "w") as f:
                    f.write(md)
                print(f"  Saved {filename}")
            time.sleep(0.5)  # be polite to the API
        except Exception as e:
            print(f"  Error fetching {scientific_name}: {e}")

if __name__ == "__main__":
    main()