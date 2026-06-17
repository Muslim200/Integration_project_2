# Diepgaande uitleg van de applicatie

## 1. Inleiding

Dit document legt uit hoe de Expertum-proof-of-concept (PoC) van binnenuit werkt. Het is bedoeld voor de student die het project mondeling moet kunnen uitleggen en verdedigen: elke component wordt beschreven, met verwijzingen naar de echte functienamen en bestanden in de code.

De PoC is een **Retrieval-Augmented Generation (RAG)**-toepassing voor klantenservice. RAG betekent: in plaats van een taalmodel zomaar een antwoord te laten verzinnen, zoeken we eerst relevante informatie op uit een eigen kennisbron en geven we die mee aan het model. Het model formuleert dan een antwoord op basis van die opgehaalde informatie. Concreet: een klant typt een supportvraag (vaak in het Nederlands), de applicatie zoekt vergelijkbare historische supporttickets en, bij technische vragen, relevante pagina's uit producthandleidingen, en vraagt een lokaal taalmodel om daarmee een bruikbaar antwoord te schrijven.

De volledige stack draait lokaal: Python met pandas, LangChain als orkestratielaag, Chroma als vectordatabank, en Ollama dat het taalmodel LLaMA 3.1 8B en het embeddingmodel `nomic-embed-text` aanbiedt. PDF-handleidingen worden ingelezen met pypdf en de gebruikersinterface is gebouwd met Streamlit.

Dit document behandelt achtereenvolgens de technologieën, de RAG-pipeline op hoog niveau, de datalaag (van CSV naar vectoren), het hart van de applicatie (vraagverwerking in `rag_app.py`), de gebruikersinterface, de configuratie, de gebruikte technieken, de evaluatie en tests, en tot slot een overzicht van alle code- en documentatiebestanden.

## 2. Overzicht van de technologieën

| Technologie | Rol in het project | Waar in de code |
|---|---|---|
| Python | Programmeertaal voor de hele applicatie | alle bestanden onder `src/` |
| pandas | Inlezen en opschonen van het CSV-ticketbestand naar een DataFrame | `src/load_data.py` (`load_ticket_dataframe`, `tickets_to_documents`) |
| LangChain | Orkestratielaag die documenten, vectoropslag, retrieval, prompt en model aan elkaar koppelt | `src/rag_app.py`, `src/build_index.py`, `src/build_manual_index.py` |
| Chroma | Vectordatabank die embeddings opslaat en op gelijkenis doorzoekbaar maakt | `src/build_index.py`, `src/build_manual_index.py`, `src/rag_app.py` |
| Ollama | Lokale runtime die het taalmodel en het embeddingmodel aanbiedt | `src/settings.py` (`OLLAMA_BASE_URL`), `src/rag_app.py` (`_make_llm`, `_make_embeddings`) |
| LLaMA 3.1 8B | Het taalmodel dat het uiteindelijke antwoord schrijft | `DEFAULT_LLM_MODEL` in `src/settings.py`, gebruikt door `_make_llm` |
| nomic-embed-text | Het embeddingmodel dat tekst omzet naar vectoren | `DEFAULT_EMBEDDING_MODEL` in `src/settings.py`, gebruikt door `_make_embeddings` |
| pypdf | Tekst uit de PDF-handleidingen halen (via LangChains `PyPDFLoader`) | `src/build_manual_index.py` (`_load_manual_pdf`) |
| Streamlit | Webinterface waar de klant een vraag stelt en het antwoord ziet | `src/streamlit_app.py` |

Een **embedding** is een vertaling van tekst naar een lijst getallen (een vector) die de betekenis van die tekst vastlegt. Teksten met een vergelijkbare betekenis krijgen vergelijkbare vectoren. Een **vectordatabank** zoals Chroma slaat die vectoren op en kan razendsnel de meest gelijkende vectoren bij een zoekopdracht teruggeven; zo vindt het systeem tickets die qua betekenis op de klantvraag lijken, ook als de exacte woorden verschillen.

## 3. De RAG-pipeline in vogelvlucht

Op hoog niveau zijn er twee fasen: eenmalig de index bouwen (offline), en daarna bij elke vraag een antwoord genereren (online).

```
INDEX BOUWEN (eenmalig, offline)
  CSV-tickets ──► pandas DataFrame ──► LangChain Documents (met metadata)
        ──► opsplitsen in chunks ──► embeddings (nomic) ──► Chroma "support_tickets"

  PDF-handleidingen ──► pypdf ──► chunks ──► embeddings (nomic) ──► Chroma "product_manuals"

VRAAG BEANTWOORDEN (per klantvraag, online)
  1. Klantvraag binnen
  2. _search_query    : Nederlandse zinnen ──► Engelse zoektermen
  3. _detect_product  : herken de productnaam in de vraag
  4. _route_ticket_type: bepaal het vraagtype (Refund/Billing/...)
  5. _extract_known_facts: haal feiten die de klant al gaf uit de vraag
  6. _retrieve_ticket_docs : zoek tickets in Chroma (met metadata-filter)
  7. _retrieve_manual_docs : zoek handleidingfragmenten (alleen bij techniek)
  8. PROMPT + REQUEST_GUIDANCE: bouw de prompt met alle context
  9. LLaMA 3.1 8B genereert het antwoord (temperatuur 0)
 10. Antwoord + gebruikte bronnen terug naar de gebruiker
```

De online-stappen 1 tot en met 10 staan allemaal in de functie `answer_question` in `src/rag_app.py`. De rest van dit document loopt eerst de offline-datalaag door en daarna stap voor stap door `answer_question`.

## 4. Datalaag: van CSV naar vectoren

Voordat er ook maar één vraag beantwoord kan worden, moet de kennis in Chroma staan. Dat gebeurt in drie bestanden.

### 4.1 `load_data.py` — CSV naar Documents

`load_ticket_dataframe` leest het CSV-bestand uit `data/raw/` met pandas in een DataFrame (een tabel) en verwijdert lege rijen. Omdat de Kaggle-dataset niet altijd dezelfde kolomnamen gebruikt, vertaalt `_resolve_columns` de echte kolomnamen via `COLUMN_ALIASES` naar vaste interne namen zoals `ticket_id`, `product`, `ticket_type`, `subject`, `description` en `resolution`.

`tickets_to_documents` zet vervolgens elke ticketrij om naar een LangChain `Document`. Een `Document` heeft twee delen:

- **`page_content`**: de leesbare tekst van het ticket, opgebouwd als regels zoals `Ticket ID`, `Product`, `Ticket type`, `Subject`, `Customer problem` en `Previous resolution`.
- **`metadata`**: een woordenboek met losse velden die later gebruikt worden om te filteren: `ticket_id`, `product`, `ticket_type`, `priority` en `status`.

`_clean_text` ruimt de tekst op: het vervangt placeholders als `{product_purchased}` door de echte productnaam en haalt overtollige spaties weg. Optioneel kan `tickets_to_documents` filteren op `ticket_type`, `product` of een `limit` (maximaal aantal rijen). Bij het direct uitvoeren van `load_data.py` toont `main` een korte preview van een paar documenten.

### 4.2 `build_index.py` — chunking, embeddings en de `support_tickets`-collectie

`build_index` doet de eigenlijke indexering:

1. Het laadt de DataFrame en zet die om naar `Documents` (via `load_data.py`).
2. Het splitst de documenten in **chunks** met `RecursiveCharacterTextSplitter` (`chunk_size=900`, `chunk_overlap=120`). Een chunk is een handzaam tekststuk; lange teksten worden in stukken geknipt zodat elke embedding een afgebakend stuk betekenis vastlegt. De `overlap` zorgt dat zinnen op de knip niet verloren gaan.
3. Het maakt embeddings met `nomic-embed-text` via Ollama en slaat de chunks in batches van 100 op in de Chroma-collectie `support_tickets` (map `data/chroma_db`).
4. Standaard wordt een bestaande index eerst gewist (`reset=True`).

Via de CLI kun je `--ticket-type`, `--product`, `--limit` en `--no-reset` meegeven. Voor de brede demo wordt zonder filters gebouwd, zodat de assistent alle vraagtypes (technical, refund, billing, delivery, cancellation) aankan.

### 4.3 `build_manual_index.py` — PDF naar de `product_manuals`-collectie

Dit bestand bouwt de tweede kennisbron. `build_manual_index` zoekt PDF's in `data/manuals/raw/`. Voor elke PDF:

1. `_infer_product_name` leidt de productnaam af uit de bestandsnaam via `PRODUCT_NAME_MAP` (bijvoorbeeld `dell_xps_manual.pdf` → `Dell XPS`).
2. `_load_manual_pdf` gebruikt LangChains `PyPDFLoader` (gebaseerd op pypdf) om de tekst per pagina te lezen. Pagina's met minder dan 80 tekens worden overgeslagen (vaak lege of louter grafische pagina's). Aan de metadata worden `source_type` (`"product_manual"`), `product`, `manual_file` en `page` toegevoegd.
3. De pagina's worden gesplitst met `RecursiveCharacterTextSplitter` (`chunk_size=900`, `chunk_overlap=150`), geëmbed met `nomic-embed-text` en in batches opgeslagen in de Chroma-collectie `product_manuals` (map `data/chroma_manuals`).

Het resultaat zijn twee gescheiden vectordatabanken: één met historische tickets en één met handleidingfragmenten.

## 5. Het hart: vraagverwerking in `rag_app.py`

Alle online-logica zit in `answer_question(question, k=4, source_mode="hybrid")`. We lopen de functie door in volgorde en bespreken elke helper die ze aanroept.

Eerst valideert `answer_question` dat `source_mode` een van `hybrid`, `tickets` of `manuals` is en controleert het of `data/chroma_db` bestaat (zo niet: foutmelding met de hint om eerst `build_index.py` te draaien). Daarna opent het de `support_tickets`-collectie via een `Chroma`-object met `_make_embeddings()` als embeddingfunctie.

### 5.1 `_search_query` — Nederlands naar Engelse zoektermen

De kerngedachte: de dataset is **Engelstalig**. Embeddings van een Nederlandse zin liggen niet altijd dicht bij Engelse tickets met dezelfde betekenis. Daarom vertaalt `_search_query` veelvoorkomende Nederlandse probleemzinnen naar Engelse zoektermen voordat er gezocht wordt. Het werkt met een woordenboek van vervangingen die **na elkaar** worden toegepast, dus de volgorde is belangrijk:

```python
"start niet meer op": "does not turn on",
"zwart scherm": "black screen",
"twee keer aangerekend": "charged twice",
"geld retour": "refund",   # staat vóór de losse regel "retour": "return"
"retour": "return",
```

Meervoudige uitdrukkingen staan bewust vóór hun deelwoorden, zodat bijvoorbeeld `geld retour` als `refund` wordt vertaald en niet eerst als `geld return` wordt verminkt. Het resultaat (`search_query`) wordt gebruikt voor de eigenlijke zoekopdracht in Chroma; de oorspronkelijke vraag blijft behouden voor de prompt.

### 5.2 `_detect_product` — productherkenning

`_known_products` leest alle unieke productnamen uit de kolom "Product Purchased" van de dataset (van lang naar kort gesorteerd, zodat een langere naam eerst matcht). `_detect_product` normaliseert de vraag met `_normalize` (lowercase, alleen letters/cijfers) en geeft de eerste productnaam terug die als deeltekst in de vraag voorkomt, of `None`. Het herkende product wordt later een metadata-filter.

### 5.3 De keyword-router: `_detect_ticket_type` en `_looks_like_technical_issue`

Dit is de eigenlijke "Dutch language support"-functie. Het vraagtype (`ticket_type`) bepaalt het metadata-filter op de tickets, en dat filter stuurt sterker dan het embeddingmodel zélf welke tickets opgehaald worden. Correcte routing is daarom de belangrijkste hefboom voor de antwoordkwaliteit.

`_detect_ticket_type` controleert de genormaliseerde vraag tegen lijsten van trefwoorden, in een **bewuste volgorde**. De eerste lijst die raak is, bepaalt het type:

1. **Refund request** — `refund`, `geld terug`, `geld retour`, `terugbetaling`, `terugvragen`, ...
2. **Cancellation request** — `cancel`, `annuleren`, `afzeggen`, `stopzetten`, `afbestellen`, ...
3. **Billing inquiry** — `bill`, `factuur`, `betaling`, `aangerekend`, `afschrijving`, ...
4. **Product inquiry** (logistiek) — `pakket`, `zending`, `trackingnummer`, `package`, `parcel`, ...
5. **Technical issue** — via `_looks_like_technical_issue` (zie hieronder)
6. **Product inquiry** (overige levering/bestelling) — `order`, `levering`, `geleverd`, `ontvangen`, ...
7. **Technical issue** (terugval) — `technical`, `problem`, `issue`, `broken`
8. Niets gevonden → `None`

De volgorde lost echte verwarringen op. Logistieke begrippen als `trackingnummer` staan vóór de technische detectie, zodat "het trackingnummer werkt niet meer" niet als technisch probleem wordt opgevat. Omgekeerd staan `geleverd` en `bezorgd` bewust ná de technische detectie: een "gisteren geleverd maar het scherm blijft zwart"-vraag moet technisch blijven, niet als pure leveringsvraag eindigen.

`_looks_like_technical_issue` geeft `True` zodra de vraag een technische uitdrukking bevat, zoals `does not turn on`, `black screen`, `wifi`, `fan`, en Nederlandse varianten als `zwart scherm`, `traag`, `ventilator`, `defect`, `kapot`, `geen geluid` en `hapert`. Deze functie heeft een dubbele rol: ze is een stap in de router én ze bepaalt later of er ook handleidingen opgehaald worden.

### 5.4 De drie routeringsmodi: `_route_ticket_type`, `_llm_detect_ticket_type` en `ROUTER_MODE`

`answer_question` roept niet `_detect_ticket_type` rechtstreeks aan, maar `_route_ticket_type`. Die kiest de strategie op basis van `ROUTER_MODE` (uit de omgevingsvariabele `RAG_ROUTER`, zie sectie 7):

- **`keyword`** (standaard): alleen de keyword-regels (`_detect_ticket_type`). Snel, deterministisch, geen extra modelaanroep.
- **`llm`**: eerst het model (`_llm_detect_ticket_type`); herkent dat niets, dan de keyword-regels als terugval.
- **`hybrid`**: eerst de keyword-regels; vinden die niets, dan het model.

`_llm_detect_ticket_type` is de eenvoudige versie van LLM-routing. Het stuurt de klantvraag plus de vijf categorieën met een korte omschrijving (uit `TICKET_TYPE_DESCRIPTIONS`) naar het model en vraagt om **alleen de categorienaam** als antwoord (platte tekst, geen JSON die geparset moet worden). Vervolgens matcht het die naam tegen de bekende categorieën. Als het model onbereikbaar is of een categorie teruggeeft die niet herkend wordt, geeft de functie `None` terug, waarna de keyword-regels het overnemen. De keyword-regels zijn dus in elke modus de terugval, zodat de applicatie blijft werken als het model niet draait.

De vijf categorieën met hun omschrijving (uit `TICKET_TYPE_DESCRIPTIONS`):

| `ticket_type` | Betekenis |
|---|---|
| Technical issue | het product werkt niet, is kapot, of gedraagt zich onverwacht |
| Refund request | de klant wil zijn geld terug |
| Billing inquiry | een vraag of probleem over een betaling, afschrijving of factuur |
| Cancellation request | de klant wil een bestelling stoppen of annuleren |
| Product inquiry | een vraag over de levering van een bestelling of over een product zelf |

### 5.5 `_extract_known_facts` — wat de klant al verteld heeft

`_extract_known_facts` haalt feiten uit de vraag die de assistent later niet opnieuw mag vragen. Het herkende product en vraagtype worden meteen als feit opgenomen. Daarnaast checkt de functie op signalen als "originele oplader", "sinds gisteren", "zwart scherm", "dubbele afschrijving" of "nooit ontvangen" en zet die om in expliciete zinnen (bijvoorbeeld: "Customer already stated there is a duplicate charge or double debit."). Worden er geen feiten gevonden, dan geeft het een neutrale boodschap terug. Deze feiten gaan als apart blok in de prompt, zodat het model niet opnieuw vraagt wat al gegeven is.

### 5.6 Retrieval: `_retrieve_ticket_docs`, `_build_filter` en `_retrieve_manual_docs`

**Tickets.** `_retrieve_ticket_docs` bouwt een **metadata-filter** uit het herkende product en/of vraagtype. Een metadata-filter beperkt de zoekopdracht tot chunks waarvan de metadata aan de voorwaarde voldoet; zo zoek je alleen binnen "Dell XPS"-tickets van het type "Technical issue". `_build_filter` zet dit om naar Chroma-syntaxis: één voorwaarde wordt het filter zelf, meerdere voorwaarden worden gecombineerd met `{"$and": [...]}`.

De zoekopdracht vraagt `k` resultaten (standaard 4). Belangrijk is de **terugval om `k` te vullen**: als het strikte filter minder dan `k` documenten oplevert, doet `_retrieve_ticket_docs` een tweede, ongefilterde zoekopdracht en vult het aan met nieuwe documenten (op basis van `ticket_id` om dubbels te vermijden) tot er `k` zijn. Zo levert het systeem altijd genoeg context, ook als het filter te streng was.

**Handleidingen.** `_retrieve_manual_docs` haalt alleen handleidingfragmenten op als dat zinvol is. Het stopt meteen als de map `data/chroma_manuals` niet bestaat. Verder haalt het standaard alleen op wanneer het vraagtype `Technical issue` is, of wanneer er een product herkend is én de zoekopdracht technisch lijkt (`_looks_like_technical_issue`). Met `force=True` (de modus `manuals`) wordt die voorwaarde overgeslagen. Als er een product herkend is, wordt ook hier een metadata-filter op `product` gezet. Voor refund-, billing-, cancellation- en leveringsvragen worden dus normaal geen handleidingen opgehaald, omdat die daar zelden relevant zijn.

### 5.7 De prompt: `PROMPT` en `REQUEST_GUIDANCE`

De opgehaalde tickets en handleidingen worden leesbaar gemaakt met `_format_docs` en `_format_manual_docs` en in de prompt gezet. Een **prompt** is de complete instructie aan het taalmodel. Deze bestaat uit twee delen:

- **De systeemprompt (`PROMPT`)** is een gedragscontract. Belangrijke regels: behandel de opgehaalde tickets als voorbeelden van *andere* klanten (nooit "ons vorige gesprek"), noem geen ticket-ID's of bronnen, gebruik handleidingen als voorkeurbron voor technische stappen, vraag niets wat de klant al gaf, stel hooguit één korte vervolgvraag, beantwoord eerst een routeringsvraag indien gesteld, antwoord in dezelfde taal als de klant, en verwijs bij escalatie naar een menselijke Expertum-supportmedewerker (niet naar externe websites of de fabrikant).
- **De per-type sturing (`REQUEST_GUIDANCE`)** geeft per categorie extra instructies. Voor een "Refund request" bijvoorbeeld: niet gaan troubleshooten maar vragen naar bestelnummer, aankoopbewijs en productconditie. Voor een "Technical issue": veilige eerstelijns-troubleshootingstappen geven. De categorie `Unknown` dient als terugval als er geen type herkend werd.

De prompt krijgt: het herkende `request_type`, de bijbehorende `request_guidance`, de `known_facts`, de oorspronkelijke `question`, de `ticket_context` en de `manual_context`.

### 5.8 Generatie: `_make_llm`, ChatOllama, temperatuur 0 en `num_ctx`

`_make_llm` maakt een `ChatOllama`-client met model `llama3.1:8b`, `temperature=0` en `num_ctx=8192`. **Temperatuur 0** maakt de generatie deterministisch: bij dezelfde invoer komt hetzelfde antwoord eruit, wat handig is voor demonstraties en evaluatie. **`num_ctx`** begrenst het contextvenster (hoeveel tekst het model in één keer leest) op 8192 tokens; het standaardvenster is veel groter dan de RAG-prompt nodig heeft en kost onnodig geheugen.

De keten `PROMPT | llm | StrOutputParser()` voert de prompt in, laat het model genereren en geeft de tekst als string terug. `answer_question` retourneert het antwoord plus de gebruikte documenten (`docs + manual_docs`).

### 5.9 `source_mode` en `main`

De parameter `source_mode` bepaalt welke bronnen meegaan: `tickets` (alleen tickets), `manuals` (alleen handleidingen, met `force=True`) of `hybrid` (beide, de standaard). Dit is wat het evaluatiescript gebruikt om bronnen te vergelijken.

`main` is de eenvoudige command-line-interface: het vraagt in een lus om een klantvraag, roept `answer_question` aan en print het antwoord plus de gebruikte tickets (`ticket_id`, `product`, `type`). Typen van `exit`, `quit` of `stop` beëindigt de lus.

## 6. De gebruikersinterface (`streamlit_app.py`)

De Streamlit-app is een webinterface die er als een echt supportportaal uitziet. Bovenaan toont `render_topbar` de status: of de vectordatabank klaar is (`CHROMA_DIR.exists()`), welk LLM en welk embeddingmodel gebruikt worden.

In het hoofdvak typt de klant een vraag in een tekstveld en klikt op **Generate**. Bij het indrukken:

1. De app bepaalt het herkende product (`_detect_product`) en vraagtype (`_detect_ticket_type`) om die als metric te tonen.
2. Het roept `answer_question(question)` aan (de standaard `hybrid`-modus) binnen een spinner en meet de tijd.
3. Het toont drie metrics: **Product**, **Request type** en **Time** (in seconden).
4. Het toont het gegenereerde antwoord in een opgemaakt vak.
5. Onder "Retrieved tickets" toont `render_ticket` elke bron. Voor een ticket: `ticket_id`, product, type, status en prioriteit, met een uitklapbaar venster voor de opgehaalde tekst. Voor een handleidingfragment: product, bestandsnaam en pagina.

Daaronder staat een statisch hulpcentrum (`render_common_questions`) met categorieën en help-artikelen die los staan van de RAG-pipeline; dat is puur uitleg-inhoud voor de klant, geen modeluitvoer.

## 7. Configuratie (`settings.py`)

`settings.py` bundelt alle instellingen op één plek:

- **Mappen**: `ROOT_DIR`, `RAW_DATA_DIR`, `RAW_MANUALS_DIR`, `PROCESSED_DATA_DIR`, `CHROMA_DIR` (tickets) en `CHROMA_MANUALS_DIR` (handleidingen).
- **Modellen en collecties**: `DEFAULT_LLM_MODEL = "llama3.1:8b"`, `DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"`, `DEFAULT_COLLECTION = "support_tickets"`, `MANUALS_COLLECTION = "product_manuals"`.
- **Generatie-instellingen**: `LLM_TEMPERATURE = 0.0` en `LLM_NUM_CTX = 8192`.
- **`ROUTER_MODE`**: gelezen uit de omgevingsvariabele `RAG_ROUTER`, met geldige waarden `keyword` (standaard), `llm` en `hybrid`. Een onbekende waarde valt automatisch terug op `keyword`.
- **`_resolve_ollama_base_url` en `OLLAMA_BASE_URL`**: een hulpfunctie voor WSL2. Op WSL2 bereikt het standaardadres `localhost:11434` meestal Ollama op Windows; lukt dat niet, dan kun je `OLLAMA_BASE_URL` of `OLLAMA_HOST` zetten. De functie normaliseert ook een bind-adres als `0.0.0.0` naar `127.0.0.1` en geeft `None` terug als er niets gezet is (dan gebruikt LangChain zijn eigen standaard).

## 8. Gebruikte technieken

Deze sectie benoemt de toegepaste technieken conceptueel en zegt waar elk in de code leeft.

- **Retrieval-Augmented Generation (RAG).** De ruggengraat: eerst relevante kennis ophalen, dan een antwoord laten genereren met die kennis als context. Leeft in `answer_question` (`src/rag_app.py`), gevoed door de twee Chroma-indexen.
- **Regelgebaseerde intent-routing gekoppeld aan een metadata-filter.** Het herkende vraagtype stelt het Chroma-metadata-filter in; dat filter bepaalt sterker dan het embeddingmodel welke tickets opgehaald worden. Dit is de dominante hefboom voor de antwoordkwaliteit. Leeft in `_detect_ticket_type` / `_looks_like_technical_issue` (router) en `_build_filter` / `_retrieve_ticket_docs` (filter).
- **Query-normalisatie als brug tussen Nederlands en een Engelstalige dataset.** Nederlandse probleemzinnen worden naar Engelse zoektermen vertaald voordat er gezocht wordt, omdat de dataset Engelstalig is. Leeft in `_search_query`.
- **Prompt-engineering: de systeemprompt als gedragscontract.** Expliciete gedragsregels (geen bronnen noemen, niets dubbel vragen, in dezelfde taal antwoorden, naar Expertum-support escaleren) plus per-type sturing. Leeft in `PROMPT` en `REQUEST_GUIDANCE`.
- **Twee kennisbronnen (tickets + handleidingen).** Tickets voor supportprocessen, handleidingen voor technische stappen. Leeft in de collecties `support_tickets` en `product_manuals`, en in `_retrieve_ticket_docs` / `_retrieve_manual_docs`.
- **Optionele LLM-/hybride routing met de regels als terugval.** Het model kan het vraagtype kiezen, maar de keyword-regels blijven altijd de terugval. Leeft in `_route_ticket_type`, `_llm_detect_ticket_type` en `ROUTER_MODE`.
- **Deterministische generatie en een begrensd contextvenster.** Temperatuur 0 voor reproduceerbare antwoorden en `num_ctx` om het geheugengebruik te beperken. Leeft in `_make_llm` en de constanten in `settings.py`.

## 9. Evaluatie en tests

### 9.1 Vergelijking van bronnen met `evaluate_variants.py`

`evaluate_variants.py` draait de met de hand geschreven testcases uit `data/evaluation/test_cases.json` door `answer_question` in drie modi: `tickets`, `manuals` en `hybrid`. Per case en per modus noteert het script het antwoord, de tijd en welke bronnen gebruikt werden (`_source_summary` onderscheidt ticket- en handleidingbronnen). Het resultaat wordt weggeschreven naar `docs/evaluatie_resultaten.md`, met per antwoord een veld **"Handmatige score: ___ / 5"** en een opmerkingenveld.

Dat is een bewuste keuze: de scores worden **met de hand** ingevuld door de evaluator volgens de rubriek in `docs/evaluatie_testplan.md` (1 = fout/niet relevant tot 5 = zeer goed). De evaluatie is dus eerlijk en menselijk beoordeeld, niet automatisch toegekend. De rubriek vraagt ook expliciet te letten op: antwoordt de assistent in dezelfde taal, wordt de juiste intentie en het juiste product herkend, en wordt er niets gevraagd dat al in de vraag stond.

De onderzoeksvraag is welke bron bij welk vraagtype het beste werkt. De verwachting: technische vragen scoren beter met `manuals` of `hybrid`, terwijl refund-, billing-, cancellation- en leveringsvragen beter scoren met `tickets`.

### 9.2 Regressietests voor de Nederlandse routing

`tests/test_dutch_routing.py` zijn unittests die de Nederlandse dekking van de keyword-router vastleggen. Ze draaien puur en deterministisch, zonder de modelstack: ze roepen rechtstreeks `_detect_ticket_type`, `_search_query` en `_extract_known_facts` aan en controleren de uitkomst. De testset bevat de vijf Nederlandse evaluatie-zinnen (die correct moeten blijven), een bredere probe van realistische Nederlandse formuleringen (billing zonder het woord `factuur`, logistieke begrippen, refund-/cancellation-synoniemen, natuurlijke defectzinnen), Engelse controlegevallen (mag niet veranderen) en specifieke randgevallen, zoals dat "geleverd maar zwart scherm" technisch blijft en dat `geld retour` niet door de losse `retour`-regel verminkt wordt. Zo wordt een verkeerde routering (die het verkeerde ticketstel zou vastpinnen) door de tests afgevangen.

Draai de tests met:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_dutch_routing -v
```

## 10. Bestandsoverzicht (code)

| Bestand | Doel |
|---|---|
| `src/__init__.py` | Maakt van `src` een Python-pakket. |
| `src/settings.py` | Centrale configuratie: mappen, modelnamen, collecties, temperatuur/`num_ctx`, `ROUTER_MODE` en de WSL2-Ollama-URL. |
| `src/load_data.py` | Leest het ticket-CSV in een DataFrame en zet rijen om naar LangChain `Documents` met metadata. |
| `src/build_index.py` | Bouwt de Chroma-index `support_tickets`: chunking, embedden met nomic en opslaan. |
| `src/build_manual_index.py` | Bouwt de Chroma-index `product_manuals` uit PDF-handleidingen via pypdf. |
| `src/rag_app.py` | Het hart: vraagverwerking, routing, retrieval, prompt, generatie en de CLI (`main`). |
| `src/streamlit_app.py` | De Streamlit-webinterface die `answer_question` aanroept en antwoord plus bronnen toont. |
| `src/evaluate_variants.py` | Draait de testcases in de modi tickets/manuals/hybrid en schrijft het evaluatierapport. |
| `tests/test_dutch_routing.py` | Regressietests die de Nederlandse routing en query-normalisatie vastleggen. |
| `scripts/setup_wsl.sh` | Eenmalige setup op WSL/Ubuntu: virtuele omgeving maken en dependencies installeren. |
| `scripts/start_app.sh` | Start de app: standaard de Streamlit-UI, met argument `cli` de terminal-Q&A. |

## 11. Documentenoverzicht

| Bestand | Doel |
|---|---|
| `docs/app_deep_dive.md` | Dit document: een diepgaande uitleg van de hele applicatie voor de mondelinge verdediging. |
| `docs/technische_documentatie.md` | Beknopte technische documentatie: architectuur, retrieval-aanpak, routing, bronnen en generatie. |
| `docs/reflectie.md` | Reflectie op bronkeuze, cloud versus lokaal LLM, datakwaliteit, taal en verbeterpunten. |
| `docs/evaluatie_testplan.md` | Het evaluatieplan: doel, onderzoeksvragen, verwachtingen, scoringsrubriek en uitvoering. |
| `docs/evaluatie_resultaten.md` | Het gegenereerde evaluatierapport met antwoorden per modus en handmatig in te vullen scores. |
| `docs/kostenanalyse.md` | Kostenvergelijking tussen een cloud-LLM en de lokale Ollama-oplossing. |
| `docs/demo_vragen.md` | Voorbeeldvragen (Engels en Nederlands) voor de demonstratie. |
| `docs/use_case_diagram.md` | Use-case-diagram en uitleg van de actoren en hun interacties. |

## 12. De applicatie draaien

De volledige stappen staan in `README.md`. In het kort:

1. Maak een virtuele omgeving en installeer de dependencies (`python3 -m venv .venv`, `pip install -r requirements.txt`).
2. Installeer Ollama en haal de modellen op: `ollama pull llama3.1:8b` en `ollama pull nomic-embed-text`.
3. Plaats de Kaggle-CSV in `data/raw/` en bouw de ticket-index: `python src/build_index.py`.
4. Plaats PDF-handleidingen in `data/manuals/raw/` en bouw de manual-index: `python src/build_manual_index.py`.
5. Start de interface: `streamlit run src/streamlit_app.py` (of `python src/rag_app.py` voor de CLI). Het script `scripts/start_app.sh` doet dit ook.

Optioneel kun je de routeringsmodus veranderen met de omgevingsvariabele `RAG_ROUTER`:

```bash
RAG_ROUTER=llm streamlit run src/streamlit_app.py     # model kiest het vraagtype
RAG_ROUTER=hybrid streamlit run src/streamlit_app.py  # eerst regels, dan model
```

Laat je `RAG_ROUTER` weg, dan gebruikt de applicatie de snelle, deterministische keyword-routing.

Qua prestaties: op een gewone laptop duurt een antwoord ongeveer 15 tot 20 seconden, vrijwel volledig de tekstgeneratie van het lokale model. Het embedden van de vraag en het zoeken in Chroma kosten samen maar een fractie van een seconde.
