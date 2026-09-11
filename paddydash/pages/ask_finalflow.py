"""Grounded chat interface for approved FinalFlow summaries."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import asdict

import streamlit as st

from paddydash.components.charts import related_plot
from paddydash.components.ui import data_type_label, evidence_panel, page_intro
from paddydash.services.ai_service import (
    answer_with_fallback,
    api_is_configured,
    get_max_ai_requests_per_session,
    get_model_name,
    prepared_data_response,
)
from paddydash.services.analytics import ChatResponse, EvidenceItem
from paddydash.services.data_service import load_dashboard_data
from paddydash.services.project_context import selected_context, project_retrieval
from paddydash.services.search_service import search_web, should_search


SUGGESTIONS = [
    "Which brand has the highest total transformed visits?",
    "Which category has the highest average daily intensity?",
    "How do weekday store-visit patterns differ?",
    "Which market has the highest average activity?",
    "How common was rain in the historical June-July observations?",
    "Compare the synthetic rainy post-match and ordinary-day scenarios.",
]


def response_to_state(response: ChatResponse) -> dict:
    return {
        "answer": response.answer,
        "evidence": [asdict(item) for item in response.evidence],
        "related_plot_id": response.related_plot_id,
        "data_type": response.data_type,
        "limitations": response.limitations,
        "mode": response.mode,
    }


def response_from_state(state: dict) -> ChatResponse:
    return ChatResponse(
        answer=state["answer"],
        evidence=[EvidenceItem(**item) for item in state["evidence"]],
        related_plot_id=state["related_plot_id"],
        data_type=state["data_type"],
        limitations=state["limitations"],
        mode=state["mode"],
    )


def show_response(response: ChatResponse, show_plot: bool = True) -> None:
    if response.mode == "openai":
        st.caption("Answer mode: OpenAI narrative grounded in prepared FinalFlow data.")
    else:
        st.caption("Answer mode: verified prepared-data response.")
    st.markdown(response.answer)
    if response.evidence or response.related_plot_id:
        data_type_label(response.data_type)
        evidence_panel(response.evidence)
    if response.limitations:
        with st.expander("Limitations", expanded=True):
            for item in response.limitations:
                st.markdown(f"- {item}")
    if show_plot and response.related_plot_id:
        st.markdown("#### Related chart")
        st.plotly_chart(
            related_plot(response.related_plot_id, load_dashboard_data()),
            width="stretch",
            theme="streamlit",
            config={"displaylogo": False},
        )


def render_ask_finalflow() -> None:
    data = load_dashboard_data()
    context = selected_context(st.session_state)
    st.caption(context['scope'] + ' | Scenario / modeled')
    page_intro(
        "Ask FinalFlow",
        "Ask questions about approved store-visit summaries, historical weather "
        "evidence, and synthetic scenario summaries. Answers include evidence, a "
        "data label, a related chart, and limitations.",
        "derived",
    )

    openai_enabled = api_is_configured()
    request_limit = get_max_ai_requests_per_session()
    if "ai_request_count" not in st.session_state:
        st.session_state.ai_request_count = 0

    mode_status = st.empty()

    def show_mode_status() -> None:
        remaining = max(0, request_limit - st.session_state.ai_request_count)
        if openai_enabled:
            mode_status.success(
                f"Secure server-side OpenAI mode is configured with "
                f"`{get_model_name()}`. AI requests remaining in this browser "
                f"session: {remaining}/{request_limit}. This best-effort allowance "
                "resets in a new browser session."
            )
        else:
            mode_status.info(
                "`OPENAI_API_KEY` is not configured. The page is using "
                "deterministic prepared-data answers; no browser-side API call "
                "is made."
            )

    show_mode_status()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "safety_token" not in st.session_state:
        st.session_state.safety_token = secrets.token_hex(16)

    st.markdown("### Ask your own question")
    st.caption(
        "Type a question about brands, categories, dates, weekdays, markets, "
        "visit distributions, reviewed historical weather, or the synthetic "
        "scenarios. Live match-day forecasts are not available. The examples "
        "below are optional shortcuts."
    )
    with st.form("finalflow_question_form", clear_on_submit=True):
        typed_question = st.text_area(
            "Your question",
            placeholder=(
                "For example: How does weekend activity compare with weekdays?"
            ),
            height=100,
            max_chars=500,
        )
        submitted = st.form_submit_button(
            "Ask FinalFlow", type="primary", width="stretch"
        )

    suggestion_header, clear_column = st.columns([4, 1])
    suggestion_header.markdown("#### Optional example questions")
    clear_slot = clear_column.empty()

    def show_clear_control() -> None:
        if clear_slot.button(
            "Clear chat",
            key="clear_chat",
            width="stretch",
            disabled=not st.session_state.chat_history,
        ):
            st.session_state.chat_history = []
            st.rerun()

    button_columns = st.columns(2)
    selected_question = None
    for index, suggestion in enumerate(SUGGESTIONS):
        if button_columns[index % 2].button(
            suggestion, key=f"suggestion_{index}", width="stretch"
        ):
            selected_question = suggestion

    if st.session_state.chat_history:
        st.markdown("### Conversation")
    for item in st.session_state.chat_history:
        with st.chat_message("user"):
            st.markdown(item["question"])
        with st.chat_message("assistant"):
            st.caption(item.get('scope', 'Earlier prepared-data answer'))
            show_response(response_from_state(item["response"]), show_plot=False)
            show_web_sources(item.get('web'))

    question = typed_question if submitted else selected_question
    if not question:
        if submitted:
            st.warning("Please enter a question before submitting.")
        show_clear_control()
        return
    question = question.strip()
    if not question:
        st.warning("Please enter a question before submitting.")
        show_clear_control()
        return
    if len(question) > 500:
        st.error("Please keep the question under 500 characters.")
        show_clear_control()
        return

    with st.chat_message("user"):
        st.markdown(question)
    external = should_search(question)
    retrieval = project_retrieval('current simulated bottleneck' if external else question, data, context)
    web = None
    if external:
        count = st.session_state.get('search_request_count', 0)
        if count >= 10:
            web = {'search_used': False, 'results': [], 'error': 'Search allowance reached for this session.'}
        else:
            st.session_state['search_request_count'] = count + 1
            web = search_web(question, summarize=False).model_dump(mode='json')
    safety_identifier = hashlib.sha256(
        st.session_state.safety_token.encode("utf-8")
    ).hexdigest()
    with st.chat_message("assistant"):
        with st.spinner("Grounding the answer in prepared FinalFlow data..."):
            if openai_enabled and st.session_state.ai_request_count >= request_limit:
                response = prepared_data_response(retrieval)
                warning = (
                    "This browser session reached its AI request allowance. "
                    "FinalFlow is showing the verified prepared-data answer instead."
                )
            else:
                if openai_enabled:
                    st.session_state.ai_request_count += 1
                    show_mode_status()
                response, warning = answer_with_fallback(
                    question, retrieval, safety_identifier=safety_identifier
                )
            if warning:
                st.warning(warning)
        show_response(response)
        show_web_sources(web)
    st.session_state.chat_history.append(
        {"question": question, "response": response_to_state(response), 'scope': context['scope'], 'web': web}
    )
    show_clear_control()


def show_web_sources(web: dict | None) -> None:
    """External snippets are separate from authoritative project metrics."""
    if web is None:
        return
    st.subheader('Web evidence')
    st.caption('External search results, not simulator inputs. Verify notices with the issuing authority.')
    if not web.get('search_used'):
        st.info('Search is unavailable. Prepared project information remains available; current alerts are not verified.')
        return
    if not web.get('results'):
        st.info('No web sources returned. Current conditions remain unverified.')
    for source in web.get('results', []):
        with st.container(border=True):
            st.text(source['title'])
            st.caption(source.get('source') or 'Web')
            st.text(source.get('snippet') or 'No snippet supplied.')
            st.link_button('Open source', source['link'])
