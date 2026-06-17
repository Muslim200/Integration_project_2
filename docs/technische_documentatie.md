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

Daarom bevat de huidige versie een regelgebaseerde routing- en normalisatielaag die uit vier delen bestaat:

- **Productherkenning.** Productnamen worden herkend in de klantvraag, bijvoorbeeld `Dell XPS`. Als een product herkend wordt, zoekt Chroma eerst binnen tickets met hetzelfde product.
- **Vraagtype-routing.** Het systeem bepaalt het vraagtype (technical, refund, billing, cancellation of product inquiry; deliveryvragen vallen onder product inquiry) en zet dat om in een Chroma-metadatafilter. Dit filter bepaalt sterker welke tickets opgehaald worden dan het embeddingmodel, dus correcte routing is de belangrijkste hefboom voor de antwoordkwaliteit.
- **Query-normalisatie.** Veelvoorkomende Nederlandse probleemzinnen worden omgezet naar Engelse zoektermen, omdat de dataset Engelstalig is.
- **Bekende feiten.** Feiten uit de vraag (zoals een dubbele afschrijving of een als bezorgd gemarkeerd pakket) worden meegegeven aan de prompt, zodat de assistent niet opnieuw vraagt wat de klant al verteld heeft.

De routing is uitgebreid zodat ook Nederlandse formuleringen herkend worden die eerder verkeerd gerouteerd werden:

- **Billing zonder het woord `factuur`:** `aangerekend`, `afschrijving`, `betaling`, en dubbele-betalingssignalen zoals `twee keer aangerekend` en `dubbele afschrijving`.
- **Logistiek vóór techniek:** logistieke begrippen zoals `pakket`, `zending` en `trackingnummer` worden herkend vóór de technische detectie, zodat een zoekgeraakt pakket niet per ongeluk als technisch probleem wordt gelabeld. `geleverd` en `bezorgd` blijven bewust onder de technische detectie, zodat een geleverd-maar-defect product wel technisch blijft.
- **Refund- en cancellation-synoniemen:** `geld retour`, `restitutie`, `terugstorten`, `afzeggen`, `intrekken` en `per ongeluk besteld`, aangevuld met order-stop- en terug-werkwoorden zoals `stopzetten`, `afbestellen`, `terugvragen` en `bedrag terugkrijgen`. Een order-stop-zin wint van een leveringssignaal, zodat `bestelling stopzetten` als cancellation geldt en niet als deliveryvraag.
- **Natuurlijke defectzinnen:** formuleringen zonder een specifiek fouttrefwoord zoals `defect`, `kapot`, `geen geluid`, `doet het niet`, `werkt onverwacht` en `hapert` worden als technisch probleem herkend. Deze regel staat bewust na billing, refund, cancellation en logistiek, zodat bijvoorbeeld een betaling- of leveringsprobleem eerst correct gerouteerd wordt.
- **Engelse logistieke begrippen:** `package`, `parcel`, `shipment` en `tracking number`, zodat ook Engelse deliveryvragen een bucket bereiken.

Voor de brede demo indexeren we alle tickets, zodat het systeem meerdere vraagtypes kan behandelen. Voor technische vragen gebruikt het systeem extra detectieregels om technische problemen zoals `black screen`, `not charging`, `slow performance`, `wifi`, `fan noise` en Nederlandse varianten zoals `zwart scherm`, `laadt niet`, `traag`, `ventilator` en `wifi` beter te herkennen.

De normalisatie past de vervangingen na elkaar toe, dus de volgorde is belangrijk: `geld retour` wordt eerst naar `refund` omgezet voordat een losse `retour`-regel zou kunnen vuren. Deze laag is vastgelegd met regressietests in `tests/test_dutch_routing.py`.

## Optionele LLM-routing

Naast de regelgebaseerde routing kan het vraagtype ook door het lokale taalmodel bepaald worden. De omgevingsvariabele `RAG_ROUTER` kiest de strategie:

- `keyword` (standaard): alleen de regelgebaseerde laag. Geen modelcall (enkele microseconden per vraag), ~67% op de vastgehouden set.
- `llm`: het lokale model (`llama3.1:8b`) classificeert elke vraag zero-shot; faalt dat, dan valt het terug op de regels. Hoogste accuratesse (~94%, want het model overschrijft ook foute regeltreffers), maar een modelcall per vraag (~1 s).
- `hybrid`: eerst de regels, en alleen bij geen treffer het model. De regels vuren op ~76% van de vragen, dus het model wordt maar in ongeveer 1 op de 4 gevallen aangeroepen. Accuratesse ~89%: tussen beide in, omdat een foute regeltreffer hier niet meer overschreven wordt.

De classificatie gebruikt een aparte JSON-prompt (`format="json"`, temperatuur 0), los van de antwoordprompt; de dispatch staat in `_route_ticket_type`. De antwoordgeneratie is in alle drie de modi identiek, dus het snelheidsverschil zit alleen in die extra classificatiecall.

`keyword` blijft bewust de standaard: deterministisch, geen extra modelcall, en in elke modus de terugval zodat een uitval van Ollama de routing niet breekt. Het ~94%-cijfer is indicatief, want een taalmodel beoordeelt hier vragen die een ander taalmodel heeft gelabeld; de reproduceerbare meting van de regelgebaseerde routing staat in `docs/eval_routing_accuracy.md`.

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

## Prestaties

Gemeten op de referentiehardware (laptop met een NVIDIA RTX 4060, 8 GB VRAM), waarbij `llama3.1:8b` volledig op de GPU past:

- Een typisch antwoord (80 tot 120 woorden) duurt warm ~13 s; de eerste vraag na inactiviteit ~22 s, inclusief het laden van het model in het VRAM.
- De tijd zit vrijwel volledig in de tekstgeneratie (~6 tot 8 woorden per seconde). Het embedden van de vraag en het ophalen uit Chroma kost samen ~55 ms, dus de retrieval is verwaarloosbaar en de routingstrategie verandert de totaaltijd nauwelijks.
- Zonder GPU valt Ollama terug op de CPU en worden deze tijden merkbaar hoger.

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
