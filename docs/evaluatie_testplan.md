# Evaluatie testplan

## Doel

We testen de impact van verschillende databronnen op de kwaliteit van de AI-assistent.

De drie varianten zijn:

- `tickets`: alleen historische supporttickets.
- `manuals`: alleen producthandleidingen.
- `hybrid`: supporttickets plus producthandleidingen.

## Onderzoeksvragen

1. Geeft de assistent betere antwoorden met enkel tickets of enkel handleidingen?
2. Werkt de hybride aanpak beter dan een enkele bron?
3. Bij welke vraagtypes zijn producthandleidingen nuttig?
4. Bij welke vraagtypes zijn supporttickets nuttiger?
5. Heeft de taal van de vraag impact op de kwaliteit van het antwoord?

## Verwachtingen

Voor technische vragen verwachten we dat handleidingen of hybrid beter scoren, omdat handleidingen officiele technische stappen bevatten.

Voor refund-, billing-, cancellation- en deliveryvragen verwachten we dat tickets beter scoren, omdat handleidingen weinig informatie bevatten over supportprocessen.

Voor Nederlandse vragen verwachten we mogelijk lagere retrievalkwaliteit, omdat de dataset en handleidingen vooral Engelstalig zijn. De applicatie bevat wel beperkte query-normalisatie om dit te verbeteren.

## Scoringsrubriek

Geef elk antwoord een score van 1 tot 5:

- 1: fout of niet relevant.
- 2: deels relevant, maar mist de vraag.
- 3: bruikbaar, maar onvolledig of wat algemeen.
- 4: goed en praktisch, met kleine verbeterpunten.
- 5: zeer goed, correct, volledig en klantgericht.

Let ook op:

- Antwoordt de assistent in dezelfde taal als de klant?
- Wordt de juiste intentie herkend?
- Wordt het juiste product herkend?
- Vraagt de assistent geen informatie die al in de vraag staat?
- Verwijst de assistent correct naar Expertum support als escalatie nodig is?
- Zijn de opgehaalde bronnen relevant?

## Uitvoering

Run eerst een kleine test:

```bash
python src/evaluate_variants.py --limit 2
```

Run daarna een specifieke case:

```bash
python src/evaluate_variants.py --case-id technical_nl_lg_route
```

Run alle cases:

```bash
python src/evaluate_variants.py
```

Het rapport wordt geschreven naar:

```text
docs/evaluatie_resultaten.md
```

Let op: dit bestand wordt telkens overschreven wanneer `evaluate_variants.py` opnieuw uitgevoerd wordt. Run de evaluatie opnieuw na belangrijke wijzigingen aan prompt, retrieval of databronnen, zodat de resultaten overeenkomen met de huidige versie van de applicatie.
