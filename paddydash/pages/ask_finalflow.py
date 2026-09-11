"""Grounded chat interface for approved FinalFlow summaries."""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import asdict

import streamlit as st

from paddydash.components.charts import related_plot
from paddydash.components.ui import data_type_label, evidence_panel, page_intro, stretch_width
from paddydash.services.ai_service import (
    answer_with_fallback,
    api_is_configured,
    get_max_ai_requests_per_session,
    prepared_data_response,
    attach_web_context,
)
from paddydash.services.analytics import ChatResponse, EvidenceItem
from paddydash.services.data_service import load_dashboard_data
from paddydash.services.project_context import selected_context, project_retrieval, question_context
from paddydash.services.search_service import search_web, should_search
from paddydash.services.search_models import SearchResponse


SUGGESTIONS = [
    "Why is this node the bottleneck?",
    "Which intervention performs best?",
    "What changes after the final whistle?",
    "How does rain affect mobility?",
    "Where should commercial activity be controlled?",
    "Which values are synthetic?",
    "Check current transit alerts.",
]


def clear_conversation() -> None:
    """Clear answers without resetting the replay or provider allowances."""
    st.session_state.chat_history = []


def response_to_state(response: ChatResponse) -> dict:
    return {
        "answer": response.answer,
        "evidence": [asdict(item) for item in response.evidence],
        "related_plot_id": response.related_plot_id,
        "data_type": response.data_type,
        "limitations": response.limitations,
        "mode": response.mode,
        "key_findings": response.key_findings,
        "recommendations": response.recommendations,
        "web_sources": response.web_sources,
        "search_used": response.search_used,
        "web_status": response.web_status,
    }


def response_from_state(state: dict) -> ChatResponse:
    return ChatResponse(
        answer=state["answer"],
        evidence=[EvidenceItem(**item) for item in state["evidence"]],
        related_plot_id=state["related_plot_id"],
        data_type=state["data_type"],
        limitations=state["limitations"],
        mode=state["mode"],
        key_findings=state.get('key_findings', []),
        recommendations=state.get('recommendations', []),
        web_sources=state.get('web_sources', []),
        search_used=state.get('search_used', False),
        web_status=state.get('web_status'),
    )


def show_response(response: ChatResponse, show_plot: bool = True) -> None:
    if response.mode == "openai":
        st.caption("Answer mode: OpenAI narrative grounded in prepared FinalFlow data.")
    else:
        st.caption("Answer mode: verified prepared-data response.")
    st.markdown(response.answer)
    if response.key_findings:
        with st.expander('Key findings'):
            for finding in response.key_findings:
                st.write(finding)
    if response.recommendations:
        with st.expander('Supported actions'):
            for recommendation in response.recommendations:
                st.write(recommendation)
    if response.evidence or response.related_plot_id:
        data_type_label(response.data_type)
        with st.expander('Project Evidence', expanded=True):
            evidence_panel(response.evidence)
            for label in sorted({item.data_type for item in response.evidence}):
                data_type_label(label)
    if response.limitations:
        with st.expander("Limitations", expanded=True):
            for item in response.limitations:
                st.markdown(f"- {item}")
    if show_plot and response.related_plot_id:
        st.markdown("#### Related chart")
        st.plotly_chart(
            related_plot(response.related_plot_id, load_dashboard_data()),
            **stretch_width(st.plotly_chart),
            theme="streamlit",
            config={"displaylogo": False},
        )


def render_ask_finalflow() -> None:
    try:
        data = load_dashboard_data()
    except (OSError, ValueError, KeyError):
        data = None
        st.warning('Some historical context is unavailable. Mobility evidence remains available.')
    context = selected_context(st.session_state)
    st.caption(context['scope'] + ' | Scenario / modeled')
    page_intro(
        "Ask FinalFlow",
        "NY/NJ corridor decision support",
        "derived",
    )

    openai_enabled = api_is_configured()
    request_limit = get_max_ai_requests_per_session()
    if "ai_request_count" not in st.session_state:
        st.session_state.ai_request_count = 0

    mode_status = st.empty()

    def show_mode_status() -> None:
        if openai_enabled:
            mode_status.caption('AI assistant')
        else:
            mode_status.info(
                ("AI assistant is unavailable because OPENAI_API_KEY is not configured."
                 if not os.environ.get('OPENAI_API_KEY', '').strip()
                 else "AI assistant is disabled for this session.")
                + " Deterministic project answers remain available."
            )

    show_mode_status()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "safety_token" not in st.session_state:
        st.session_state.safety_token = secrets.token_hex(16)

    typed_question = st.chat_input('Ask FinalFlow', max_chars=500, key='finalflow_chat_input')

    suggestion_header, clear_column = st.columns([4, 1])
    suggestion_header.markdown("#### Suggested questions")
    clear_slot = clear_column.empty()

    def show_clear_control() -> None:
        if clear_slot.button(
            "Clear conversation",
            key="clear_chat",
            **stretch_width(st.button),
            disabled=not st.session_state.chat_history,
            on_click=clear_conversation,
        ):
            st.rerun()

    selected_question = None
    with st.expander('Explore a decision', expanded=not st.session_state.chat_history):
        button_columns = st.columns(2)
        for index, suggestion in enumerate(SUGGESTIONS):
            if button_columns[index % 2].button(
                suggestion, key=f"suggestion_{index}", **stretch_width(st.button)
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

    question = typed_question or selected_question
    if question is None:
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
    context = question_context('current simulated bottleneck' if external else question, context)
    retrieval = project_retrieval('current simulated bottleneck' if external else question, data, context)
    web = None
    if external:
        count = st.session_state.get('search_request_count', 0)
        if count >= 10:
            web = {'search_used': False, 'results': [], 'error': 'Search allowance reached for this session.'}
        else:
            st.session_state['search_request_count'] = count + 1
            web = search_web(question, summarize=False).model_dump(mode='json')
        retrieval = attach_web_context(retrieval, SearchResponse.model_validate({'query': question, **web}))
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
    st.session_state.chat_history = st.session_state.chat_history[-20:]
    show_clear_control()


def show_web_sources(web: dict | None) -> None:
    """External snippets are separate from authoritative project metrics."""
    if web is None:
        return
    st.subheader('Web Sources')
    st.caption('Web evidence: unverified search excerpts, not simulator inputs. Sources may disagree or be stale; verify notices with the issuing authority.')
    if not web.get('search_used'):
        st.info('Live web search unavailable. Current public information could not be checked. Prepared project information remains available.')
        return
    st.badge('Web search used', icon=':material/search:')
    if not web.get('results'):
        st.info('No web sources returned. Current conditions remain unverified.')
    for source in web.get('results', []):
        with st.container(border=True):
            st.link_button(source['title'], source['link'])
            st.caption(source.get('source') or 'Web')
            st.text(source.get('snippet') or 'No snippet supplied.')
            st.caption('Date: ' + (source.get('date') or 'Not supplied by source'))
