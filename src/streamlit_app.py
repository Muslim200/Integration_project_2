from __future__ import annotations

import html
import time

import streamlit as st

from rag_app import answer_question, _detect_product, _detect_ticket_type
from settings import CHROMA_DIR, DEFAULT_EMBEDDING_MODEL, DEFAULT_LLM_MODEL


CATEGORIES = [
    "Recommended",
    "Shipping and Delivery",
    "Returns and Refunds",
    "Orders",
    "Billing",
    "Technical Support",
]

HELP_TOPICS = [
    {
        "title": "Find a missing package marked as delivered",
        "category": "Shipping and Delivery",
        "recommended": True,
        "summary": "What customers can check when tracking says delivered but the package is not there.",
        "content": [
            "Check the delivery address and tracking details first.",
            "Look around the delivery location, reception desk, mailbox area, or safe place.",
            "Ask household members or neighbours whether they accepted the package.",
            "If the package is still missing, contact support with the order number and tracking link.",
        ],
    },
    {
        "title": "Understand delivery times",
        "category": "Shipping and Delivery",
        "recommended": True,
        "summary": "What to do when tracking has not updated or the estimated delivery date has passed.",
        "content": [
            "Check the latest tracking event and the estimated delivery window.",
            "Small delays can happen during carrier handover or busy periods.",
            "If tracking has not changed for several days, support can review the order status.",
            "Provide the order number, tracking number, and delivery address.",
        ],
    },
    {
        "title": "Return a product",
        "category": "Returns and Refunds",
        "recommended": True,
        "summary": "Information customers usually need before sending a product back.",
        "content": [
            "Prepare the order number and purchase confirmation.",
            "Describe why the item is being returned.",
            "Keep the original packaging and accessories when possible.",
            "Support will confirm whether the item is eligible and provide the next steps.",
        ],
    },
    {
        "title": "Request a refund",
        "category": "Returns and Refunds",
        "recommended": True,
        "summary": "How refund requests are checked and what information support needs.",
        "content": [
            "Provide the order number, product name, and reason for the refund.",
            "Include photos if the item arrived damaged or incomplete.",
            "Support may need to verify the product condition and return status.",
            "Refund timing can depend on payment method and return processing.",
        ],
    },
    {
        "title": "Cancel an order before shipping",
        "category": "Orders",
        "recommended": False,
        "summary": "What customers should do when they ordered the wrong item.",
        "content": [
            "Contact support as soon as possible with the order number.",
            "Cancellation is usually easier before the order has shipped.",
            "If the order has already shipped, support may suggest a return instead.",
            "Do not place a second order until the first order status is confirmed.",
        ],
    },
    {
        "title": "Check an incorrect or duplicate charge",
        "category": "Billing",
        "recommended": True,
        "summary": "How support can investigate unexpected billing or invoice issues.",
        "content": [
            "Provide the order number and the amount charged.",
            "Check whether one charge is still pending with the bank.",
            "Share the invoice or payment confirmation if available.",
            "Support can compare the order record with the payment status.",
        ],
    },
    {
        "title": "Product does not turn on",
        "category": "Technical Support",
        "recommended": True,
        "summary": "First checks for products that do not power on or respond.",
        "content": [
            "Use the original charger or power cable when possible.",
            "Charge the device for at least 30 minutes.",
            "Check whether the power button, cable, or outlet is working.",
            "If the product still does not respond, support may need to investigate repair or replacement options.",
        ],
    },
    {
        "title": "Product keeps freezing or disconnecting",
        "category": "Technical Support",
        "recommended": False,
        "summary": "Basic checks for unstable products, freezing, or intermittent problems.",
        "content": [
            "Restart the product and check whether the problem returns.",
            "Check for updates if the product uses software or firmware.",
            "Remove connected accessories and test again.",
            "If the issue continues, provide support with the product name and when the problem occurs.",
        ],
    },
]


st.set_page_config(
    page_title="Expertum Support",
    page_icon="E",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Expertum AI Support Assistant",
    },
)

st.markdown(
    """
    <style>
    :root {
        --bg: #f5f7fb;
        --panel: #ffffff;
        --border: #d7deea;
        --text: #111827;
        --muted: #667085;
        --accent: #155eef;
        --accent-soft: #eef4ff;
        --success-soft: #ecfdf3;
        --success: #067647;
    }

    #MainMenu, footer, [data-testid="stHeader"], [data-testid="stToolbar"] {
        display: none;
    }

    .stApp {
        background: var(--bg);
        color: var(--text);
    }

    .main .block-container {
        max-width: 1120px;
        padding-top: 26px;
        padding-bottom: 44px;
    }

    h1, h2, h3, p, label, span {
        color: var(--text);
    }

    .topbar {
        display: flex;
        justify-content: space-between;
        gap: 18px;
        align-items: flex-start;
        margin-bottom: 18px;
    }

    .brand {
        display: flex;
        gap: 14px;
        align-items: center;
    }

    .logo {
        width: 44px;
        height: 44px;
        border-radius: 8px;
        background: var(--accent);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 22px;
    }

    .title {
        margin: 0;
        font-size: 28px;
        line-height: 1.1;
        font-weight: 780;
    }

    .subtitle {
        margin: 5px 0 0 0;
        color: var(--muted);
        font-size: 14px;
    }

    .status-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 8px;
    }

    .pill {
        border: 1px solid var(--border);
        background: var(--panel);
        border-radius: 999px;
        padding: 7px 11px;
        color: var(--muted);
        font-size: 13px;
        white-space: nowrap;
    }

    .pill strong {
        color: var(--text);
    }

    .ready {
        background: var(--success-soft);
        border-color: #abefc6;
        color: var(--success);
        font-weight: 700;
    }

    .section-title {
        font-size: 16px;
        font-weight: 750;
        margin: 0 0 10px 0;
    }

    .answer-box {
        background: #ffffff;
        border: 1px solid var(--border);
        border-left: 4px solid var(--accent);
        border-radius: 8px;
        padding: 18px 20px;
        line-height: 1.58;
        font-size: 15px;
        white-space: pre-wrap;
    }

    .ticket-card {
        border: 1px solid var(--border);
        background: #ffffff;
        border-radius: 8px;
        padding: 13px 15px;
        margin-bottom: 10px;
    }

    .ticket-card strong {
        color: var(--text);
    }

    .ticket-meta {
        margin-top: 4px;
        color: var(--muted);
        font-size: 13px;
    }

    .helper-text {
        color: var(--muted);
        font-size: 14px;
        margin: -4px 0 12px 0;
    }

    .faq-card {
        min-height: 132px;
        border: 1px solid var(--border);
        background: #ffffff;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 14px;
    }

    .faq-title {
        color: var(--text);
        font-size: 15px;
        font-weight: 750;
        margin-bottom: 7px;
    }

    .faq-copy {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.45;
    }

    .help-shell {
        margin-top: 24px;
        border-top: 1px solid var(--border);
        padding-top: 24px;
    }

    .help-title {
        font-size: 23px;
        font-weight: 780;
        margin: 0 0 12px 0;
    }

    .topic-card {
        border: 1px solid var(--border);
        background: #ffffff;
        border-radius: 8px;
        padding: 16px 17px;
        min-height: 126px;
        margin-bottom: 10px;
    }

    .topic-title {
        color: var(--text);
        font-size: 16px;
        font-weight: 750;
        margin-bottom: 7px;
    }

    .topic-summary {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.45;
    }

    .article-panel {
        border: 1px solid var(--border);
        background: #ffffff;
        border-radius: 8px;
        padding: 24px;
    }

    .breadcrumb {
        color: var(--accent);
        font-size: 13px;
        font-weight: 650;
        margin-bottom: 14px;
    }

    .article-title {
        font-size: 28px;
        line-height: 1.15;
        font-weight: 780;
        margin: 0 0 13px 0;
    }

    .article-copy {
        color: var(--muted);
        font-size: 15px;
        line-height: 1.55;
        margin-bottom: 15px;
    }

    .step-list {
        margin: 0;
        padding-left: 20px;
    }

    .step-list li {
        margin-bottom: 8px;
        color: var(--text);
        line-height: 1.5;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid var(--border);
        border-radius: 8px;
        background: #ffffff;
    }

    [data-testid="stTextArea"] textarea {
        background: #ffffff;
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 8px;
        min-height: 165px;
        font-size: 15px;
    }

    [data-testid="stTextArea"] textarea::placeholder {
        color: #98a2b3;
        opacity: 1;
    }

    div.stButton > button {
        border-radius: 7px;
        min-height: 42px;
        font-weight: 700;
        color: var(--text);
        background: #ffffff;
        border: 1px solid var(--border);
    }

    div.stButton > button:hover {
        border-color: var(--accent);
        color: var(--accent);
        background: var(--accent-soft);
    }

    div.stButton > button[kind="primary"] {
        background: var(--accent);
        border-color: var(--accent);
        color: #ffffff;
    }

    div.stButton > button[kind="primary"]:hover {
        background: #004eeb;
        border-color: #004eeb;
        color: #ffffff;
    }

    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px 14px;
    }

    [data-testid="stMetric"] * {
        color: var(--text);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def clear_question() -> None:
    st.session_state["question"] = ""


def select_category(category: str) -> None:
    st.session_state["help_category"] = category


def select_topic(title: str) -> None:
    st.session_state["selected_topic"] = title


def get_selected_topic() -> dict:
    selected_title = st.session_state.get("selected_topic")
    if selected_title:
        for topic in HELP_TOPICS:
            if topic["title"] == selected_title:
                return topic
    return HELP_TOPICS[0]


def render_topbar() -> None:
    vector_status = "Ready" if CHROMA_DIR.exists() else "Missing"
    vector_class = "pill ready" if CHROMA_DIR.exists() else "pill"

    st.markdown(
        f"""
        <div class="topbar">
            <div class="brand">
                <div class="logo">E</div>
                <div>
                    <h1 class="title">Expertum Support</h1>
                    <p class="subtitle">AI assistant for customer support tickets</p>
                </div>
            </div>
            <div class="status-row">
                <div class="{vector_class}">Vector DB: <strong>{vector_status}</strong></div>
                <div class="pill">LLM: <strong>{DEFAULT_LLM_MODEL}</strong></div>
                <div class="pill">Embeddings: <strong>{DEFAULT_EMBEDDING_MODEL}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ticket(index: int, doc) -> None:
    metadata = doc.metadata
    if metadata.get("source_type") == "product_manual":
        product = html.escape(str(metadata.get("product", "Unknown product")))
        manual_file = html.escape(str(metadata.get("manual_file", "Unknown manual")))
        page = html.escape(str(metadata.get("page", "")))
        st.markdown(
            f"""
            <div class="ticket-card">
                <strong>{index}. Product manual</strong>
                <div class="ticket-meta">
                    {product} · {manual_file} · Page {page}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Retrieved manual context"):
            st.write(doc.page_content)
        return

    ticket_id = html.escape(str(metadata.get("ticket_id", "Unknown")))
    product = html.escape(str(metadata.get("product", "Unknown product")))
    ticket_type = html.escape(str(metadata.get("ticket_type", "Unknown type")))
    status = html.escape(str(metadata.get("status", "Unknown status")))
    priority = html.escape(str(metadata.get("priority", "Unknown priority")))

    st.markdown(
        f"""
        <div class="ticket-card">
            <strong>{index}. Ticket {ticket_id}</strong>
            <div class="ticket-meta">
                {product} · {ticket_type} · {status} · {priority}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Retrieved context"):
        st.write(doc.page_content)


def render_common_questions() -> None:
    if "help_category" not in st.session_state:
        st.session_state["help_category"] = "Recommended"

    st.markdown(
        """
        <div class="help-shell">
            <div class="help-title">Find more solutions</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    search_query = st.text_input(
        "Search help topics",
        label_visibility="collapsed",
        placeholder="Search delivery, returns, refunds, billing, cancellations...",
    )

    nav_col, cards_col = st.columns([0.27, 0.73], gap="large")

    with nav_col:
        for category in CATEGORIES:
            st.button(
                category,
                key=f"category_{category}",
                use_container_width=True,
                type="primary" if st.session_state["help_category"] == category else "secondary",
                on_click=select_category,
                args=(category,),
            )

    active_category = st.session_state["help_category"]
    normalized_search = search_query.strip().lower()
    topics = []
    for topic in HELP_TOPICS:
        matches_category = active_category == "Recommended" and topic["recommended"]
        matches_category = matches_category or topic["category"] == active_category
        searchable_text = f"{topic['title']} {topic['summary']} {topic['category']}".lower()
        matches_search = not normalized_search or normalized_search in searchable_text
        if matches_category and matches_search:
            topics.append(topic)

    if not topics and normalized_search:
        topics = [
            topic
            for topic in HELP_TOPICS
            if normalized_search in f"{topic['title']} {topic['summary']} {topic['category']}".lower()
        ]

    with cards_col:
        if not topics:
            st.info("No help topics found. Try another search term.")
        else:
            grid_cols = st.columns(2)
            for index, topic in enumerate(topics):
                with grid_cols[index % 2]:
                    st.markdown(
                        f"""
                        <div class="topic-card">
                            <div class="topic-title">{html.escape(topic["title"])}</div>
                            <div class="topic-summary">{html.escape(topic["summary"])}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.button(
                        "Read article",
                        key=f"topic_{topic['title']}",
                        use_container_width=True,
                        on_click=select_topic,
                        args=(topic["title"],),
                    )

    topic = get_selected_topic()
    steps = "".join(f"<li>{html.escape(step)}</li>" for step in topic["content"])
    st.markdown(
        f"""
        <div class="article-panel">
            <div class="breadcrumb">{html.escape(topic["category"])} / Help article</div>
            <h2 class="article-title">{html.escape(topic["title"])}</h2>
            <p class="article-copy">{html.escape(topic["summary"])}</p>
            <ol class="step-list">{steps}</ol>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_topbar()

with st.container(border=True):
    st.markdown('<div class="section-title">Customer request</div>', unsafe_allow_html=True)

    question = st.text_area(
        "Customer request",
        key="question",
        label_visibility="collapsed",
        placeholder="Example: I want a refund for my Canon DSLR Camera. What should I do?",
    )

    action_col, clear_col, spacer_col = st.columns([0.22, 0.18, 0.60], vertical_alignment="bottom")
    with action_col:
        submitted = st.button("Generate", type="primary", use_container_width=True)
    with clear_col:
        st.button("Clear", use_container_width=True, on_click=clear_question)
    with spacer_col:
        st.empty()

if submitted:
    if not question.strip():
        st.warning("Enter a customer request first.")
    else:
        detected_product = _detect_product(question) or "Not detected"
        detected_type = _detect_ticket_type(question) or "Not detected"

        start_time = time.perf_counter()
        with st.spinner("Generating response..."):
            answer, docs = answer_question(question)
        elapsed = time.perf_counter() - start_time

        metric_a, metric_b, metric_c = st.columns(3)
        metric_a.metric("Product", detected_product)
        metric_b.metric("Request type", detected_type)
        metric_c.metric("Time", f"{elapsed:.1f}s")

        st.markdown('<div class="section-title">Suggested response</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="answer-box">{html.escape(answer)}</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title" style="margin-top: 18px;">Retrieved tickets</div>', unsafe_allow_html=True)
        for index, doc in enumerate(docs, start=1):
            render_ticket(index, doc)

render_common_questions()
