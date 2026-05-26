# Expertum AI Klantenservice PoC

Deze proof-of-concept beantwoordt klantvragen op basis van historische supporttickets en producthandleidingen met een RAG-pipeline.

## 1. Dataset plaatsen

Download de Kaggle dataset:

https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset

Plaats het CSV-bestand in:

```text
data/raw/
```

## 2. Python omgeving maken

Gebruik WSL/Ubuntu in deze projectmap:

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3.12-venv
```

Maak daarna de virtuele omgeving:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Ollama modellen installeren

Installeer Ollama en download daarna:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Controleer of Ollama draait:

```bash
ollama list
```

## 4. Vectorindex bouwen

Voor de brede demo indexeren we alle supporttickets. Zo kan de assistent technische vragen, refunds, billing, delivery en cancellations behandelen.

```bash
source .venv/bin/activate
python src/build_index.py
```

Optioneel kun je voor onderzoek of debugging filteren:

```bash
python src/build_index.py --ticket-type "Technical issue"
python src/build_index.py --product "GoPro Hero"
python src/build_index.py --limit 1000
```

## 4b. Producthandleidingen indexeren

Plaats de PDF-handleidingen in:

```text
data/manuals/raw/
```

Gebruik bestandsnamen zoals:

```text
dell_xps_manual.pdf
canon_dslr_manual.pdf
lg_oled_manual.pdf
gopro_hero_manual.pdf
hp_pavilion_manual.pdf
samsung_galaxy_manual.pdf
```

Installeer nieuwe dependencies als dat nog niet gebeurd is:

```bash
pip install -r requirements.txt
```

Bouw daarna de manual-index:

```bash
python src/build_manual_index.py
```

De applicatie gebruikt bij technische vragen supporttickets en haalt daarnaast relevante stukken uit de producthandleidingen op als die beschikbaar zijn.

## 5. Vragen stellen

```bash
source .venv/bin/activate
python src/rag_app.py
```

Of start de Streamlit-interface:

```bash
streamlit run src/streamlit_app.py
```

Voorbeeldvraag:

```text
My Dell XPS does not turn on since yesterday. I am using the original charger, but it does not respond. What should I do?
```

Andere goede demovragen:

```text
My GoPro Hero sometimes works and sometimes stops responding. What can I try?
```

```text
My LG Smart TV has compatibility issues with an external device. How can I fix this?
```

```text
My Canon DSLR Camera is not charging properly. What are the first troubleshooting steps?
```

## Projectkeuze

We gebruiken lokaal `llama3.1:8b` via Ollama. Dit model is sterk genoeg voor een RAG-PoC, gratis in gebruik en privacyvriendelijker dan een cloud-LLM.

Voor de beste resultaten stellen we demovragen in het Engels, omdat de dataset Engelstalig is. De applicatie kan Nederlandse vragen gedeeltelijk normaliseren, maar Engelse vragen leveren betere retrieval op.

## Evaluatie

Voor het onderzoek kunnen dezelfde vragen getest worden in drie modi:

- `tickets`: alleen historische tickets.
- `manuals`: alleen producthandleidingen.
- `hybrid`: tickets plus handleidingen.

Run een korte evaluatie:

```bash
python src/evaluate_variants.py --limit 2
```

Run alle testcases:

```bash
python src/evaluate_variants.py
```

Het rapport komt in:

```text
docs/evaluatie_resultaten.md
```
