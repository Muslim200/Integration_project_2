# Objectieve routing-accuratesse (onafhankelijk gegenereerd)

Testset: **ontwikkel (ingezien)** -- bron `eval_generated_labeled_dev.json`.

De testvragen zijn door onafhankelijke modellen geschreven (qwen3 / gemma3 / llama3.1) en door een *ander* model blind geclassificeerd. De grondwaarheid is dat blinde label, niet mijn oordeel. De routingfunctie `_detect_ticket_type` is rechtstreeks uit git geladen op drie versies.

- before = `eb3c12f^` (routing vóór de fix)
- pr2 = `eb3c12f` (de eerste routing/normalisatie-uitbreiding)
- v2 = werkkopie (kleine vervolgfix: defect-/geluid-, stopzetten- en terug-verba)

Gegenereerde cases: **79**. Met blind label: **79**. Cross-model overeenstemming: **49** -- de sterkste grondwaarheid.

## Accuratesse tegenover de onafhankelijke grondwaarheid

| set | before | pr2 | v2 |
|-----|--------|-----|----|
| overeenstemmende set | 33% (16/49) | 43% (21/49) | **63% (31/49)** |
| volledige gelabelde set | 27% (21/79) | 37% (29/79) | **47% (37/79)** |

## Per categorie (overeenstemmende set, grondwaarheid-bucket)

| categorie | n | before | pr2 | v2 |
|-----------|---|--------|-----|----|
| Billing inquiry | 10 | 20% (2/10) | 50% (5/10) | 50% (5/10) |
| Cancellation request | 11 | 27% (3/11) | 27% (3/11) | 73% (8/11) |
| Product inquiry | 8 | 25% (2/8) | 50% (4/8) | 50% (4/8) |
| Refund request | 9 | 33% (3/9) | 33% (3/9) | 44% (4/9) |
| Technical issue | 11 | 55% (6/11) | 55% (6/11) | 91% (10/11) |

v2 tegenover before (overeenstemmende set): **15** beslissingen naar correct, **0** naar fout.

## Eerlijke restbeperking

De vragen zijn modelgegenereerd synthetisch Nederlands, geen gelogde Belgische klanttickets. Wat hier is weggenomen, is *auteurs*-bias in zowel de formuleringen als de labels; wat blijft, is dat dit synthetische data is. De v2-regels zijn ontworpen op de ontwikkelset; het eerlijke generalisatiecijfer is dat op de vastgehouden set.
