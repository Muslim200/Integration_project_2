from __future__ import annotations

import re

from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama, OllamaEmbeddings

from load_data import load_ticket_dataframe
from settings import CHROMA_DIR, DEFAULT_COLLECTION, DEFAULT_EMBEDDING_MODEL, DEFAULT_LLM_MODEL
from settings import CHROMA_MANUALS_DIR, MANUALS_COLLECTION
from settings import LLM_NUM_CTX, LLM_TEMPERATURE, OLLAMA_BASE_URL


def _ollama_kwargs() -> dict:
    """Shared connection kwargs for Ollama clients."""
    kwargs: dict = {}
    if OLLAMA_BASE_URL:
        kwargs["base_url"] = OLLAMA_BASE_URL
    return kwargs


def _make_llm() -> ChatOllama:
    return ChatOllama(
        model=DEFAULT_LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        num_ctx=LLM_NUM_CTX,
        **_ollama_kwargs(),
    )


def _make_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=DEFAULT_EMBEDDING_MODEL, **_ollama_kwargs())


REQUEST_GUIDANCE = {
    "Cancellation request": (
        "The customer wants to cancel an order. Do not ask why if the reason is already clear, "
        "for example accidental order or wrong item. Ask only for operational missing information: "
        "order number, account email, product/model if not provided, and whether the order has shipped. "
        "Explain that cancellation is normally only possible before shipping; if shipped, support should discuss return options."
    ),
    "Refund request": (
        "The customer wants a refund. Do not troubleshoot unless the customer explicitly asks for repair help. "
        "Ask for order number, proof of purchase, product condition, reason for refund if not already stated, "
        "and whether the item was returned or arrived damaged."
    ),
    "Billing inquiry": (
        "The customer has a payment or invoice issue. Do not suggest product troubleshooting. "
        "Ask for order number, invoice/payment reference, charged amount, expected amount, and date of charge."
    ),
    "Product inquiry": (
        "The customer asks about an order, delivery, or product information. Focus on order status, tracking, "
        "delivery address, carrier details, and whether support should investigate."
    ),
    "Technical issue": (
        "The customer has a technical problem. Provide safe first-line troubleshooting steps. "
        "Ask only for missing technical details that are needed, such as model, charger/cable, connected device, or when it started. "
        "Do not ask for an on-screen error message if the customer says the screen is black or there is no display. "
        "If the customer asks whether to report it as a technical issue or a return, answer that routing question first. "
        "Usually recommend starting as a technical issue first; if basic checks do not resolve it or the product arrived defective, "
        "advise escalation to return or replacement options."
    ),
    "Unknown": (
        "Identify the most likely support intent from the customer's wording. Ask at most one concise clarification question "
        "if the request cannot be handled safely."
    ),
}


PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a helpful customer support assistant for Expertum. "
                "The retrieved historical tickets are examples from other customers, not conversations with the current customer. "
                "Never call them 'our previous conversations' and never imply the current customer already said those things. "
                "Do not mention historical tickets, previous cases, sources, context, or ticket IDs in the customer-facing answer. "
                "Use the retrieved historical ticket context as the main source for policy, process, and similar cases. "
                "Use product manual context as the preferred source for technical steps when it is available. "
                "Do not mention unrelated products from the context. "
                "Before writing the answer, silently identify: the customer's main intent, facts already provided, missing information, and the next best action. "
                "Do not ask for information the customer already provided. "
                "If a fact appears under 'Known facts already provided by the customer', do not ask the customer to confirm it again. "
                "You may briefly acknowledge known facts and continue with the next troubleshooting or support step. "
                "Do not ask for the reason when the customer already gave a reason. "
                "Do not ask impossible or illogical questions, such as asking what error message appears on a screen that the customer says is black. "
                "Only ask a follow-up question when it is truly necessary; ask at most one concise follow-up question. "
                "If the customer asks which support route to choose, answer that routing question first before giving troubleshooting steps. "
                "Answer the customer's actual intent: for refund requests, explain the refund process and information needed; "
                "do not suggest software updates, resets, charger checks, or other troubleshooting unless the customer asks for technical help. "
                "For technical issues, provide safe first-line troubleshooting steps and advise escalation if the issue remains. "
                "If previous resolutions are missing or low quality, say what support should verify next. "
                "Do not tell the customer to check external official websites or contact the product manufacturer's support team. "
                "If escalation is needed, refer to a human Expertum support agent instead. "
                "Answer in the same language as the customer question. "
                "Do not add a translation of your answer in parentheses. "
                "Be practical, polite, and concise. End with the next best action, not with unnecessary questions."
            ),
        ),
        (
            "human",
            "Detected request type: {request_type}\n\n"
            "Request-specific guidance:\n{request_guidance}\n\n"
            "Known facts already provided by the customer:\n{known_facts}\n\n"
            "Customer question:\n{question}\n\n"
            "Relevant historical tickets:\n{ticket_context}\n\n"
            "Relevant product manual context:\n{manual_context}\n\n"
            "Answer:",
        ),
    ]
)


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _known_products() -> list[str]:
    df = load_ticket_dataframe()
    product_column = next(
        (column for column in df.columns if _normalize(column) == "product purchased"),
        None,
    )
    if not product_column:
        return []
    products = sorted(
        {str(value).strip() for value in df[product_column].dropna() if str(value).strip()},
        key=len,
        reverse=True,
    )
    return products


def _detect_product(question: str) -> str | None:
    normalized_question = _normalize(question)
    for product in _known_products():
        if _normalize(product) in normalized_question:
            return product
    return None


def _search_query(question: str) -> str:
    replacements = {
        "start niet meer op": "does not turn on",
        "kan hem niet aan zetten": "does not turn on",
        "kan hem niet aanzetten": "does not turn on",
        "gaat niet aan": "does not turn on",
        "reageert niet": "does not respond",
        "traag": "slow performance",
        "heel traag": "very slow performance",
        "opstarten": "startup boot",
        "ventilator": "fan",
        "lawaai": "loud noise",
        "veel lawaai": "loud fan noise",
        "zwart scherm": "black screen",
        "scherm blijft zwart": "screen stays black",
        "wel geluid": "sound works",
        "geen beeld": "no picture",
        "geen wifi": "wifi connection problem",
        "verbindt niet": "does not connect",
        "loopt vast": "freezes",
        "originele oplader": "original charger",
        "laadt niet": "not charging",
        "opladen": "charging",
        "werkt soms": "intermittent issue sometimes works",
        "bestelling": "order",
        "annuleren": "cancel",
        "per ongeluk": "accidental",
        "verkeerde": "wrong",
        "verzonden": "shipped",
        "geleverd": "delivered",
        # Multi-word phrases before their substrings: bare "retour"->"return"
        # would otherwise fire inside "geld retour".
        "staat als bezorgd": "marked as delivered",
        "nooit ontvangen": "never received",
        "niet ontvangen": "not received",
        "geld retour": "refund",
        "trackingnummer": "tracking number",
        "bezorgd": "delivered",
        "pakket": "package",
        "zending": "shipment",
        "retour melden": "report return",
        "retour": "return",
        "terug sturen": "return",
        "terugsturen": "return",
        "terugbetaling": "refund",
        "probleem": "problem issue",
        # Billing vocabulary (specific multi-word phrases before their substrings).
        "twee keer aangerekend": "charged twice",
        "dubbel aangerekend": "charged twice",
        "dubbele afschrijving": "double charge",
        "dubbel afgeschreven": "double charged",
        "aangerekend": "charged",
        "afschrijving": "charge",
        "afgeschreven": "charged",
        "gefactureerd": "invoiced",
        "factuur": "invoice",
        "betaling": "payment",
        "afzeggen": "cancel",
        "intrekken": "cancel",
        # order-stop and malfunction/refund verb variants (mirror _detect_ticket_type)
        "stopzetten": "cancel",
        "afbestellen": "cancel",
        "terugvragen": "refund",
        "defect": "defective",
        "stukgegaan": "broken",
        "kapot": "broken",
        "geen geluid": "no sound",
        "hapert": "stutters glitchy",
        "crasht": "crashes",
    }
    query = question.lower()
    for dutch, english in replacements.items():
        query = query.replace(dutch, english)
    return query


def _looks_like_technical_issue(question: str) -> bool:
    normalized = _normalize(question)
    technical_phrases = [
        "does not turn on",
        "does not respond",
        "not charging",
        "black screen",
        "screen stays black",
        "no sound",
        "freezes",
        "freeze",
        "slow",
        "performance",
        "fan",
        "loud noise",
        "startup",
        "boot",
        "wifi",
        "wi fi",
        "battery",
        "connect",
        "disconnect",
        "error message",
        "werkt niet",
        "reageert niet",
        "laadt niet",
        "scherm",
        "zwart scherm",
        "traag",
        "ventilator",
        "lawaai",
        "opstarten",
        "loopt vast",
        "wifi",
        "batterij",
        "verbindt niet",
        # Generic "broken product" phrasings; reached only after billing/refund/
        # cancel/logistics are ruled out, so "betaling werkt niet" routes earlier.
        "defect",
        "kapot",
        "stukgegaan",
        "geen geluid",
        "geen beeld",
        "doet het niet",
        "doet niet",
        "doen niet",
        "werkt onverwacht",
        "hapert",
        "crasht",
        "beeldkwaliteit",
        "glitch",
    ]
    return any(phrase in normalized for phrase in technical_phrases)


def _detect_ticket_type(question: str) -> str | None:
    normalized = _normalize(question)
    if any(
        word in normalized
        for word in [
            "refund", "reimburse", "money back",
            "terugbetaling", "terugbetalen", "geld terug", "geld retour",
            "restitutie", "terugstorten",
            "terugvragen", "geld terugkrijgen", "bedrag terugkrijgen",
            "bedrag terug", "geld weer terug",
        ]
    ):
        return "Refund request"
    if any(
        word in normalized
        for word in [
            "cancel", "cancellation", "wrong order",
            "annuleren", "annuleer", "annulering", "per ongeluk besteld",
            "afzeggen", "intrekken",
            # order-stop synonyms, before the delivery fallback so "stopzetten" reads as cancel
            "stopzetten", "stop zetten", "stopgezet", "afbestellen",
            "annulatie", "bestelling stoppen", "bestelling te stoppen", "order stoppen",
        ]
    ):
        return "Cancellation request"
    if any(
        word in normalized
        for word in [
            "bill", "billing", "charged", "invoice", "double charge",
            "factuur", "gefactureerd", "betaling", "betaald", "aangerekend",
            "afschrijving", "afgeschreven", "dubbel betaald", "twee keer betaald",
        ]
    ):
        return "Billing inquiry"
    # Logistics nouns route to delivery before the technical check (so
    # "trackingnummer werkt niet" isn't grabbed as technical). "geleverd"/"bezorgd"
    # are excluded -- they co-occur with faults -- and stay in the delivery list below.
    if any(
        word in normalized
        for word in [
            "pakket", "pakketje", "zending", "verzending",
            "trackingnummer", "tracking", "track and trace",
            "package", "parcel", "shipment", "tracking number",
        ]
    ):
        return "Product inquiry"
    if _looks_like_technical_issue(question):
        return "Technical issue"
    if any(
        word in normalized
        for word in [
            "order", "delivery", "shipping", "shipped", "arrived", "delivered", "received",
            "bestelling", "levering", "bezorgd", "bezorging",
            "geleverd", "afgeleverd", "ontvangen",
        ]
    ):
        return "Product inquiry"
    if "technical" in normalized or "problem" in normalized or "issue" in normalized or "broken" in normalized:
        return "Technical issue"
    return None


def _extract_known_facts(question: str, product: str | None, ticket_type: str | None) -> str:
    normalized = _normalize(question)
    facts: list[str] = []

    if product:
        facts.append(f"Product/model is already provided: {product}.")
    if ticket_type:
        facts.append(f"Request type is already identified: {ticket_type}.")

    if any(phrase in normalized for phrase in ["original charger", "originele oplader"]):
        facts.append("Customer already stated they are using the original charger.")
    if any(phrase in normalized for phrase in ["charger", "oplader", "power adapter"]):
        facts.append("Customer already mentioned the charger or power adapter.")
    if any(phrase in normalized for phrase in ["since yesterday", "sinds gisteren", "yesterday", "gisteren"]):
        facts.append("Customer already stated when the issue started.")
    if any(phrase in normalized for phrase in ["does not respond", "reageert niet"]):
        facts.append("Customer already stated the product does not respond.")
    if any(phrase in normalized for phrase in ["does not turn on", "start niet meer op", "gaat niet aan"]):
        facts.append("Customer already stated the product does not turn on.")
    if any(phrase in normalized for phrase in ["black screen", "zwart scherm", "screen stays black"]):
        facts.append("Customer already stated the screen is black or does not show a picture.")
    if any(phrase in normalized for phrase in ["sound", "geluid", "no picture"]):
        facts.append("Customer already stated sound is present or the issue is display-related.")
    if any(phrase in normalized for phrase in ["delivered yesterday", "gisteren geleverd"]):
        facts.append("Customer already stated the product was delivered yesterday.")
    if any(phrase in normalized for phrase in ["technical or return", "technisch probleem of als retour", "retour melden"]):
        facts.append("Customer is asking whether this should be handled as a technical issue or a return.")
    if any(phrase in normalized for phrase in ["accidental", "per ongeluk", "wrong", "verkeerde"]):
        facts.append("Customer already gave the reason: accidental or wrong order/product.")
    if any(
        phrase in normalized
        for phrase in [
            "charged twice", "double charge", "twee keer aangerekend",
            "dubbel aangerekend", "dubbele afschrijving", "dubbel afgeschreven",
        ]
    ):
        facts.append("Customer already stated there is a duplicate charge or double debit.")
    if any(phrase in normalized for phrase in ["marked as delivered", "staat als geleverd", "staat als bezorgd"]):
        facts.append("Customer already stated the package is marked as delivered.")
    if any(phrase in normalized for phrase in ["never received", "nooit ontvangen", "niet ontvangen"]):
        facts.append("Customer already stated the package was never received.")

    if not facts:
        return "No specific known facts extracted. Avoid repeating obvious details from the question."

    return "\n".join(f"- {fact}" for fact in facts)


def _format_docs(docs) -> str:
    if not docs:
        return "No historical ticket context available."
    return "\n\n".join(
        f"Source {index + 1}\n{doc.page_content}" for index, doc in enumerate(docs)
    )


def _format_manual_docs(docs) -> str:
    if not docs:
        return "No product manual context available."
    return "\n\n".join(
        (
            f"Manual source {index + 1}\n"
            f"Product: {doc.metadata.get('product', '')}\n"
            f"File: {doc.metadata.get('manual_file', '')}\n"
            f"Page: {doc.metadata.get('page', '')}\n"
            f"{doc.page_content}"
        )
        for index, doc in enumerate(docs)
    )


def _build_filter(filters: dict[str, str]) -> dict | None:
    if len(filters) == 1:
        return filters
    if len(filters) > 1:
        return {"$and": [{key: value} for key, value in filters.items()]}
    return None


def _retrieve_ticket_docs(vectorstore: Chroma, search_query: str, product: str | None, ticket_type: str | None, k: int):
    search_kwargs = {"k": k}
    filters = {}
    if product:
        filters["product"] = product
    if ticket_type:
        filters["ticket_type"] = ticket_type
    filter_value = _build_filter(filters)
    if filter_value:
        search_kwargs["filter"] = filter_value

    docs = vectorstore.as_retriever(search_kwargs=search_kwargs).invoke(search_query)

    if len(docs) < k and filters:
        fallback_docs = vectorstore.as_retriever(search_kwargs={"k": k}).invoke(search_query)
        seen_ids = {doc.metadata.get("ticket_id") for doc in docs}
        for doc in fallback_docs:
            if doc.metadata.get("ticket_id") not in seen_ids:
                docs.append(doc)
            if len(docs) >= k:
                break

    return docs


def _retrieve_manual_docs(
    search_query: str,
    product: str | None,
    ticket_type: str | None,
    k: int = 3,
    force: bool = False,
):
    if not CHROMA_MANUALS_DIR.exists():
        return []
    if not force and ticket_type != "Technical issue" and not (product and _looks_like_technical_issue(search_query)):
        return []

    embeddings = _make_embeddings()
    manual_store = Chroma(
        collection_name=MANUALS_COLLECTION,
        persist_directory=str(CHROMA_MANUALS_DIR),
        embedding_function=embeddings,
    )

    search_kwargs = {"k": k}
    if product:
        search_kwargs["filter"] = {"product": product}

    return manual_store.as_retriever(search_kwargs=search_kwargs).invoke(search_query)


def answer_question(question: str, k: int = 4, source_mode: str = "hybrid") -> tuple[str, list]:
    if source_mode not in {"hybrid", "tickets", "manuals"}:
        raise ValueError("source_mode must be one of: hybrid, tickets, manuals")

    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            "No vector database found. Run `python src/build_index.py` first."
        )

    embeddings = _make_embeddings()
    vectorstore = Chroma(
        collection_name=DEFAULT_COLLECTION,
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
    )

    search_query = _search_query(question)
    product = _detect_product(question)
    ticket_type = _detect_ticket_type(question)
    known_facts = _extract_known_facts(question, product, ticket_type)

    docs = []
    manual_docs = []
    if source_mode in {"hybrid", "tickets"}:
        docs = _retrieve_ticket_docs(vectorstore, search_query, product, ticket_type, k)
    if source_mode in {"hybrid", "manuals"}:
        manual_docs = _retrieve_manual_docs(
            search_query,
            product,
            ticket_type,
            force=source_mode == "manuals",
        )

    ticket_context = _format_docs(docs)
    manual_context = _format_manual_docs(manual_docs)

    llm = _make_llm()
    chain = PROMPT | llm | StrOutputParser()
    answer = chain.invoke(
        {
            "question": question,
            "request_type": ticket_type or "Unknown",
            "request_guidance": REQUEST_GUIDANCE[ticket_type or "Unknown"],
            "known_facts": known_facts,
            "ticket_context": ticket_context,
            "manual_context": manual_context,
        }
    )
    return answer, docs + manual_docs


def main() -> None:
    print("Expertum AI klantenservice")
    print("Typ een klantvraag. Typ 'exit' om te stoppen.")
    print()

    while True:
        question = input("Klantvraag: ").strip()
        if question.lower() in {"exit", "quit", "stop"}:
            break
        if not question:
            continue

        answer, docs = answer_question(question)
        print()
        print("Antwoord:")
        print(answer)
        print()
        print("Gebruikte tickets:")
        for index, doc in enumerate(docs, start=1):
            metadata = doc.metadata
            print(
                f"{index}. ticket_id={metadata.get('ticket_id', '')} "
                f"product={metadata.get('product', '')} "
                f"type={metadata.get('ticket_type', '')}"
            )
        print()


if __name__ == "__main__":
    main()
