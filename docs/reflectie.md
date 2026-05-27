# Reflectie

## Supporttickets of producthandleiding

Supporttickets zijn nuttig omdat ze echte klantproblemen bevatten. Ze tonen hoe klanten hun probleem formuleren en welke oplossingen eerder gebruikt zijn. Een producthandleiding is meestal gestructureerder en betrouwbaarder, maar bevat minder praktijkvoorbeelden.

Voor deze proof-of-concept gebruiken we beide bronnen. Supporttickets zijn nuttig voor supportprocessen zoals refund, billing, delivery en cancellation. Producthandleidingen zijn vooral nuttig voor technische vragen, omdat ze officiele stappen en productspecificaties bevatten.

## Cloud-LLM versus lokaal LLM

Een cloud-LLM levert meestal betere taal en sterkere redenering. Een lokaal LLM is goedkoper in gebruik en geeft meer controle over data, maar vraagt voldoende hardware en kan minder nauwkeurig zijn.

## Invloed van datakwaliteit

De kwaliteit van de brondata bepaalt sterk hoe goed RAG werkt. Tickets met duidelijke beschrijvingen en oplossingen leveren betere antwoorden op. Tickets zonder oplossing, dubbele tickets of heel korte beschrijvingen kunnen slechte context opleveren.

In de gekozen Kaggle dataset staan sommige velden met placeholders zoals `{product_purchased}` en sommige resoluties zijn weinig bruikbaar of grammaticaal zwak. Daarom is extra preprocessing nodig en blijft de kwaliteit van het antwoord beperkt door de kwaliteit van de historische tickets.

## Taal

De dataset en handleidingen zijn vooral Engelstalig. Engelse klantvragen leveren daardoor van nature betere retrievalresultaten op dan Nederlandse klantvragen. Om die beperking te verkleinen bevat de proof-of-concept een uitgebreide regelgebaseerde routing- en normalisatielaag voor Nederlandse vragen. De technische werking staat in `docs/technische_documentatie.md`.

Het belangrijkste inzicht is dat het herkende vraagtype (technisch, refund, billing, cancellation of een product- of deliveryvraag) het Chroma-metadatafilter instelt. Dat filter bepaalt sterker welke tickets worden opgehaald dan het embeddingmodel zelf. Een verkeerde routing pint daardoor het verkeerde ticketstel vast en stuurt de klant soms onterecht naar een externe partij. De echte hefboom voor Nederlandse kwaliteit is dus betere routing, niet een ander embeddingmodel.

We hebben twee zwaardere alternatieven getest en bewust niet overgenomen. Automatische vertaling van de vraag naar het Engels met het LLM gaf netto slechtere antwoorden en is verworpen. Een meertalig embeddingmodel (`bge-m3`) scoorde op de Nederlandse cases gelijk aan `nomic-embed-text` en gaf bovendien af en toe een instabiele embedding, dus dat is evenmin overgenomen.

Het effect van de routinglaag is gemeten met een before/after-test waarin alleen de routing verschilt en alle andere stappen identiek blijven (zelfde embedding, temperatuur 0, modus `tickets`). Op de twaalf officiele evaluatiecases verandert de routing niet: die vragen gebruiken woorden die de oude routing ook al correct herkende (zoals `geld terug`, `annuleren` en sterke technische signalen). Bij temperatuur 0 leidt gelijke routing tot exact hetzelfde antwoord, dus daar is geen regressie en blijft de score 12 op 12. De officiele set kan deze fix dus per definitie niet meten.

Om de winst objectief en zonder eigen oordeel te meten, hebben we de testvragen door andere taalmodellen laten schrijven en door weer een ander model laten indelen in een categorie. Die onafhankelijke indeling geldt als referentie, niet onze eigen beoordeling. De vragen waarop we de routing uiteindelijk beoordelen, zijn bovendien pas gegenereerd nadat de regels al vastlagen, zodat we toetsen of de aanpak ook werkt op formuleringen die we zelf nooit gezien hebben. Op die vastgehouden set koos de routing duidelijk vaker de juiste categorie: ongeveer twee op de drie vragen tegenover iets meer dan een op de drie vóór dit werk (67% tegenover 39% van de vragen waarover twee modellen het eens waren), en geen enkele vraag werd slechter ingedeeld. De vooruitgang zit precies bij de vraagtypes die we wilden opvangen, namelijk billing, annuleringen, refunds en technische klachten zonder duidelijk trefwoord, terwijl de algemenere productvragen gelijk bleven.

De absolute score blijft beperkt: de regelgebaseerde laag herkent nog niet elke Nederlandse formulering, en de testvragen zijn door modellen bedacht en niet afkomstig van echte Belgische klanten. De meting toont vooral dat de uitbreiding netto vooruitgang geeft zonder achteruitgang, niet dat het probleem volledig is opgelost. De volledige cijfers en de methode staan in `docs/eval_routing_accuracy.md`.

Nederlandse vragen blijven belangrijk voor de evaluatie, omdat Expertum in een Belgische context werkt. Daarom bevat de evaluatieset zowel Engelse als Nederlandse testcases.

## Verbeteringen

Mogelijke verbeteringen voor een volgende versie:

- Betere opschoning van rommelige ticketbeschrijvingen.
- Een evaluatieset maken met vaste testvragen en verwachte antwoorden.
- Een meertalige dataset gebruiken voor Nederlandse of Belgische klantvragen.

In de huidige uitgebreide versie zijn producthandleidingen toegevoegd voor een selectie producten. Dit maakt technische antwoorden betrouwbaarder, omdat de assistent niet alleen afhankelijk is van historische tickets waarvan de resoluties soms onvolledig of rommelig zijn.

In dezelfde versie is de Nederlandse routing- en normalisatielaag flink uitgebreid. Nederlandse formuleringen zonder het woord `factuur` (zoals `twee keer aangerekend` of `dubbele afschrijving`), logistieke begrippen zoals `pakket` en `trackingnummer`, synoniemen voor refund en cancellation zoals `geld retour` en `afzeggen`, en natuurlijke defect- en order-stopzinnen zoals `kapot`, `geen geluid` en `stopzetten` worden nu correct herkend. Dit verbetert vooral realistische Nederlandse vragen, zonder de bestaande Engelse en officiele Nederlandse testcases te verslechteren. De afweging tegenover een ander embeddingmodel staat in de sectie Taal.

## Evaluatiebevindingen

De evaluatie vergelijkt drie varianten:

- Alleen tickets.
- Alleen handleidingen.
- Hybrid: tickets plus handleidingen.

De verwachting is dat technische vragen beter scoren met handleidingen of hybrid, terwijl refund-, billing-, cancellation- en deliveryvragen beter scoren met tickets. De definitieve scores worden ingevuld in `docs/evaluatie_resultaten.md` na het uitvoeren van de testcases.
