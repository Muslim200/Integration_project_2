# Technische documentatie

## Architectuur

De proof-of-concept gebruikt een RAG-pipeline:

1. Tickets worden ingeladen uit een CSV-bestand.
2. Elke ticket wordt omgezet naar een tekstfragment met metadata.
3. De tekstfragmenten worden omgezet naar embeddings.
4. De embeddings worden opgeslagen in Chroma.
5. Bij een klantvraag zoekt LangChain relevante tickets en, indien nuttig, relevante handleidingfragmenten.
6. LLaMA 3.1 8B genereert een antwoord op basis van de gevonden context.

## Retrieval-aanpak

De eerste versie gebruikte alleen semantische zoekopdrachten. Dit gaf soms slechte resultaten, bijvoorbeeld wanneer de klantvraag over een Dell XPS ging maar de opgehaalde tickets over andere producten gingen.

Daarom bevat de huidige versie twee verbeteringen:

- Productnamen worden herkend in de klantvraag, bijvoorbeeld `Dell XPS`.
- Als een product herkend wordt, zoekt Chroma eerst binnen tickets met hetzelfde product.
- Veelvoorkomende Nederlandse probleemzinnen worden genormaliseerd naar Engelse zoektermen, omdat de dataset Engelstalig is.

Voor de brede demo indexeren we alle tickets, zodat het systeem meerdere vraagtypes kan behandelen. Voor technische vragen gebruikt het systeem extra detectieregels om technische problemen zoals `black screen`, `not charging`, `slow performance`, `wifi`, `fan noise` en Nederlandse varianten zoals `zwart scherm`, `laadt niet`, `traag`, `ventilator` en `wifi` beter te herkennen.

## Tweede databron: producthandleidingen

De uitgebreide versie gebruikt naast historische supporttickets ook producthandleidingen als kennisbron.

Er zijn twee Chroma-indexen:

- `support_tickets`: historische tickets uit de Kaggle dataset.
- `product_manuals`: PDF-handleidingen van geselecteerde producten.

Bij technische vragen zoekt de applicatie eerst relevante tickets op en haalt daarna ook relevante manual-fragmenten op voor hetzelfde product. De prompt instrueert het LLM om handleidingen als voorkeurbron te gebruiken voor technische stappen, terwijl tickets vooral dienen als praktijkvoorbeelden.

Voor refund-, billing-, cancellation- en deliveryvragen gebruikt het systeem vooral tickets, omdat producthandleidingen daar meestal minder relevant zijn.

De huidige manual-index bevat handleidingen voor:

- Canon DSLR Camera
- Dell XPS
- GoPro Hero
- HP Pavilion
- LG OLED
- Samsung Galaxy

## Antwoordgeneratie

De prompt bevat regels om klantgerichte antwoorden te verbeteren:

- Historische tickets worden behandeld als voorbeelden van andere klanten, niet als vorige gesprekken met dezelfde klant.
- De assistent mag geen ticket-ID's of bronnen noemen in het klantantwoord.
- De assistent mag geen informatie opnieuw vragen die de klant al gegeven heeft.
- De assistent antwoordt in dezelfde taal als de klantvraag.
- Bij technische problemen gebruikt de assistent handleidingen als voorkeurbron voor concrete stappen.
- Bij escalatie verwijst de assistent naar een menselijke Expertum support agent.
- Automatische vertalingen tussen haakjes worden verwijderd uit het antwoord.

## Evaluatiemodus

Voor het onderzoek is een evaluatiescript toegevoegd:

```bash
python src/evaluate_variants.py
```

Dit script test dezelfde vragen in drie modi:

- `tickets`: alleen historische tickets.
- `manuals`: alleen producthandleidingen.
- `hybrid`: beide bronnen.

Het rapport wordt opgeslagen in `docs/evaluatie_resultaten.md`.

## Technologieen

- Python
- Pandas
- LangChain
- Chroma
- Ollama
- LLaMA 3.1 8B
- nomic-embed-text

## Dataset

We gebruiken de Kaggle Customer Support Ticket Dataset:

https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset

Voor betere resultaten beperken we de eerste versie tot tickets met een duidelijke beschrijving en eventueel een resolutie.

## Demo

Aanbevolen commando om de index te bouwen:

```bash
python src/build_index.py
python src/build_manual_index.py
```

Aanbevolen demovraag:

```text
My Dell XPS does not turn on since yesterday. I am using the original charger, but it does not respond. What should I do?
```
