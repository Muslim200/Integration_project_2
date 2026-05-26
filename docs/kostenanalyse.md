# Kostenanalyse

## Alternatieven

Voor Expertum vergelijken we minstens twee opties:

1. Cloud-LLM, bijvoorbeeld OpenAI GPT of Google Gemini.
2. Lokale LLM via Ollama, bijvoorbeeld LLaMA 3.1 8B.

## Lokale optie

Voordelen:

- Geen kosten per vraag.
- Meer controle over data.
- Geschikt voor een proof-of-concept op beperkte schaal.

Nadelen:

- Vereist een laptop of server met voldoende geheugen.
- Antwoorden zijn meestal minder sterk dan bij de beste cloudmodellen.
- Installatie en beheer liggen bij het team zelf.

## Cloud optie

Voordelen:

- Hoge antwoordkwaliteit.
- Snelle integratie.
- Geen lokale hardware nodig.

Nadelen:

- Kosten per token of per request.
- Klantdata gaat naar een externe provider.
- Afhankelijkheid van internet en provider.

## Voorlopige keuze

Voor de proof-of-concept kiezen we lokaal voor Ollama met LLaMA 3.1 8B. Dit past goed bij de opdracht omdat de oplossing gratis te gebruiken is, privacyvriendelijker is en voldoende kwaliteit biedt voor een RAG-demo.

## Kostenfactoren

Belangrijke kostenfactoren:

- Hardware of server waarop het lokale model draait.
- Tijd voor installatie en onderhoud.
- Eventuele cloudkosten bij een cloud-LLM.
- Ontwikkeltijd voor preprocessing, retrieval en evaluatie.

Voor de PoC zijn de gebruikskosten van de lokale optie nul, buiten de bestaande laptop/server en ontwikkeltijd.

## Impact van producthandleidingen

Het toevoegen van producthandleidingen verhoogt vooral de ontwikkel- en onderhoudskost:

- Handleidingen moeten verzameld en correct benoemd worden.
- PDF's moeten verwerkt worden naar tekstfragmenten.
- Er is extra opslag nodig voor een tweede vectorindex.
- Bij nieuwe producten moet de handleiding toegevoegd en opnieuw geindexeerd worden.

De gebruikskost blijft lokaal wel beperkt, omdat embeddings en generatie via Ollama lokaal draaien.
