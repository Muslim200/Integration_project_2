# Objectieve routing-accuratesse (onafhankelijk gegenereerd)

Testset: **set** -- bron `eval_generated_labeled.json`.

De testvragen zijn door onafhankelijke modellen geschreven (qwen3 / gemma3 / llama3.1) en door een *ander* model blind geclassificeerd. De grondwaarheid is dat blinde label, niet mijn oordeel. De routingfunctie `_detect_ticket_type` is rechtstreeks uit git geladen op drie versies.

- before = `eb3c12f^` (routing vóór de fix)
- pr2 = `eb3c12f` (de eerste routing/normalisatie-uitbreiding)
- v2 = werkkopie (kleine vervolgfix: defect-/geluid-, stopzetten- en terug-verba)

Gegenereerde cases: **86**. Met blind label: **86**. Cross-model overeenstemming: **66** -- de sterkste grondwaarheid.

## Accuratesse tegenover de onafhankelijke grondwaarheid

| set | before | pr2 | v2 |
|-----|--------|-----|----|
| overeenstemmende set | 39% (26/66) | 45% (30/66) | **67% (44/66)** |
| volledige gelabelde set | 38% (33/86) | 42% (36/86) | **60% (52/86)** |

## Per categorie (overeenstemmende set, grondwaarheid-bucket)

| categorie | n | before | pr2 | v2 |
|-----------|---|--------|-----|----|
| Billing inquiry | 7 | 29% (2/7) | 86% (6/7) | 86% (6/7) |
| Cancellation request | 15 | 60% (9/15) | 60% (9/15) | 93% (14/15) |
| Product inquiry | 15 | 40% (6/15) | 40% (6/15) | 40% (6/15) |
| Refund request | 14 | 14% (2/14) | 14% (2/14) | 57% (8/14) |
| Technical issue | 15 | 47% (7/15) | 47% (7/15) | 67% (10/15) |

v2 tegenover before (overeenstemmende set): **18** beslissingen naar correct, **0** naar fout.

## Eerlijke restbeperking

De vragen zijn modelgegenereerd synthetisch Nederlands, geen gelogde Belgische klanttickets. Wat hier is weggenomen, is *auteurs*-bias in zowel de formuleringen als de labels; wat blijft, is dat dit synthetische data is. De v2-regels zijn ontworpen op de ontwikkelset; het eerlijke generalisatiecijfer is dat op de vastgehouden set.
