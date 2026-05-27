"""Regression tests for Dutch ticket-type routing.

These lock in the rule-based router's Dutch coverage (``_detect_ticket_type`` in
``src/rag_app.py``). The router sets the Chroma metadata filter, so a misroute
pins the wrong ticket set and degrades the answer regardless of the embedding
model -- which is exactly the lever for Dutch answer quality. A broad Dutch probe
previously misrouted 7/13 cases (billing/delivery gaps + a greedy technical
heuristic); these tests guard the fix.

Pure (no running stack), deterministic, model-independent. Run:
    PYTHONPATH=src .venv/bin/python -m unittest tests.test_dutch_routing -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from rag_app import (  # noqa: E402
    _detect_ticket_type,
    _extract_known_facts,
    _search_query,
)

# (question, expected_ticket_type). Mix of the five evaluation cases (known-good)
# and the broader probe set that exposed the billing/delivery/synonym gaps.
DUTCH_ROUTING_CASES = [
    # --- the five evaluation Dutch cases (must stay correct) ---
    ("Mijn Dell XPS start niet meer op sinds gisteren. Ik gebruik de originele oplader, maar hij reageert niet.", "Technical issue"),
    ("Mijn LG OLED TV is gisteren geleverd, maar het scherm blijft zwart terwijl ik wel geluid hoor. Moet ik dit als technisch probleem of als retour melden?", "Technical issue"),
    ("Mijn HP Pavilion verbindt niet meer met wifi, terwijl mijn andere apparaten wel internet hebben.", "Technical issue"),
    ("Mijn Canon DSLR Camera is aangekomen met een beschadigde lens. Ik wil geen vervanging maar mijn geld terug.", "Refund request"),
    ("Ik heb per ongeluk het verkeerde LG OLED model besteld en wil mijn bestelling annuleren voordat die verzonden wordt.", "Cancellation request"),
    # --- billing: Dutch without "factuur" (previously misrouted) ---
    ("Ik ben twee keer aangerekend voor mijn HP Pavilion bestelling, maar kreeg maar een bevestiging.", "Billing inquiry"),
    ("Er staat een dubbele afschrijving op mijn rekening voor de Sony PlayStation.", "Billing inquiry"),
    ("Ik heb betaald voor mijn Dell XPS maar zie de betaling niet terug.", "Billing inquiry"),
    # --- delivery / product-inquiry: Dutch logistics nouns (previously misrouted) ---
    ("Mijn pakket staat als bezorgd maar ik heb het nooit ontvangen.", "Product inquiry"),
    ("Wanneer wordt mijn Canon DSLR Camera verzonden? De levering is al laat.", "Product inquiry"),
    # distinctive logistics nouns must win over the greedy "werkt niet" technical heuristic
    ("Mijn zending is kwijt, het trackingnummer werkt niet meer.", "Product inquiry"),
    # --- refund / cancellation synonyms (previously misrouted) ---
    ("Ik wil mijn geld retour voor de beschadigde Canon DSLR Camera.", "Refund request"),
    ("Kan ik mijn order voor de LG OLED nog afzeggen voordat hij weg is?", "Cancellation request"),
]

# English controls: routing must be unchanged by the Dutch-coverage additions.
ENGLISH_CONTROL_CASES = [
    ("My Dell XPS does not turn on since yesterday.", "Technical issue"),
    ("I want my money back for the damaged Canon DSLR Camera.", "Refund request"),
    ("I was charged twice for my HP Pavilion order.", "Billing inquiry"),
]

# English delivery: previously routed to None (the "package"/"delivered" nouns were
# missing). The publisher's delivery_en_missing_package case must now reach a bucket.
ENGLISH_DELIVERY_CASES = [
    ("My package is marked as delivered, but I never received it. What should I do?", "Product inquiry"),
]


class TestDutchTicketRouting(unittest.TestCase):
    def test_dutch_cases_route_correctly(self):
        for question, expected in DUTCH_ROUTING_CASES:
            with self.subTest(question=question):
                self.assertEqual(_detect_ticket_type(question), expected)


class TestEnglishControlsUnchanged(unittest.TestCase):
    def test_english_cases_route_correctly(self):
        for question, expected in ENGLISH_CONTROL_CASES:
            with self.subTest(question=question):
                self.assertEqual(_detect_ticket_type(question), expected)


# The eval's "gisteren geleverd maar scherm blijft zwart" must stay Technical:
# "geleverd"/"bezorgd" are intentionally kept below the technical heuristic so a
# delivered-but-faulty product is not misclassified as a pure delivery question.
class TestDeliveryDoesNotShadowTechnical(unittest.TestCase):
    def test_delivered_but_faulty_stays_technical(self):
        self.assertEqual(
            _detect_ticket_type(
                "Mijn LG OLED is gisteren bezorgd maar het scherm blijft zwart."
            ),
            "Technical issue",
        )


class TestEnglishDeliveryRoutes(unittest.TestCase):
    def test_english_delivery_reaches_product_inquiry(self):
        for question, expected in ENGLISH_DELIVERY_CASES:
            with self.subTest(question=question):
                self.assertEqual(_detect_ticket_type(question), expected)


# _search_query normalizes Dutch phrasing to English for retrieval. It applies
# replacements sequentially, so substring ordering matters; these guard both the
# new billing/delivery terms and that a specific phrase is not mangled by a bare
# substring rule that runs later.
class TestSearchQueryNormalization(unittest.TestCase):
    def test_billing_phrases_normalize(self):
        self.assertIn("charged twice", _search_query("ik ben twee keer aangerekend"))
        self.assertIn("double charge", _search_query("een dubbele afschrijving op mijn rekening"))

    def test_delivery_phrases_normalize(self):
        self.assertIn("never received", _search_query("pakket bezorgd maar nooit ontvangen"))
        self.assertIn("tracking number", _search_query("het trackingnummer werkt niet"))

    def test_geld_retour_not_mangled_by_bare_retour(self):
        # "retour" -> "return" must not fire inside "geld retour" (-> "geld return").
        normalized = _search_query("ik wil mijn geld retour")
        self.assertIn("refund", normalized)
        self.assertNotIn("return", normalized)


class TestKnownFactsExtraction(unittest.TestCase):
    def test_double_debit_fact(self):
        facts = _extract_known_facts("er staat een dubbele afschrijving op mijn rekening", None, "Billing inquiry")
        self.assertIn("duplicate charge or double debit", facts)

    def test_never_received_fact(self):
        facts = _extract_known_facts("mijn pakket staat als bezorgd maar nooit ontvangen", None, "Product inquiry")
        self.assertIn("never received", facts)
        self.assertIn("marked as delivered", facts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
