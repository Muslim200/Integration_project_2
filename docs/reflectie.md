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

De dataset en handleidingen zijn vooral Engelstalig. Engelse klantvragen leveren daardoor meestal betere retrievalresultaten op dan Nederlandse klantvragen. De proof-of-concept ondersteunt Nederlandse vragen gedeeltelijk met query-normalisatie, bijvoorbeeld door `zwart scherm`, `traag`, `originele oplader` en `annuleren` om te zetten naar Engelse zoektermen.

Nederlandse vragen blijven belangrijk voor de evaluatie, omdat Expertum in een Belgische context werkt. Daarom bevat de evaluatieset zowel Engelse als Nederlandse testcases.

## Verbeteringen

Mogelijke verbeteringen voor een volgende versie:

- Betere opschoning van rommelige ticketbeschrijvingen.
- Een evaluatieset maken met vaste testvragen en verwachte antwoorden.
- Een meertalige dataset gebruiken voor Nederlandse of Belgische klantvragen.

In de huidige uitgebreide versie zijn producthandleidingen toegevoegd voor een selectie producten. Dit maakt technische antwoorden betrouwbaarder, omdat de assistent niet alleen afhankelijk is van historische tickets waarvan de resoluties soms onvolledig of rommelig zijn.

## Evaluatiebevindingen

De evaluatie vergelijkt drie varianten:

- Alleen tickets.
- Alleen handleidingen.
- Hybrid: tickets plus handleidingen.

De verwachting is dat technische vragen beter scoren met handleidingen of hybrid, terwijl refund-, billing-, cancellation- en deliveryvragen beter scoren met tickets. De definitieve scores worden ingevuld in `docs/evaluatie_resultaten.md` na het uitvoeren van de testcases.
