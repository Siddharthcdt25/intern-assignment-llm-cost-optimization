from __future__ import annotations

import json
from dataclasses import dataclass

from shared.billing import CostSession
from shared.kb import load_article
from shared.llm import ChatMessage, LlmClient
from shared.tools import format_thread, get_order, get_ticket

from question1.agent import parse_resolution


@dataclass
class TicketResolution:
    action: str
    kb_article: str


class SupportPipeline:
    """
    Optimized four-node ShopAssist pipeline.

    Triage   -> LLM-based decision
    Retrieve -> Local knowledge-base retrieval
    Compose  -> Local resolution construction
    Audit    -> Local validation
    """

    def __init__(self, session: CostSession | None = None):
        self.session = session or CostSession()
        self.llm = LlmClient(self.session)

    def handle_ticket(self, ticket_id: str) -> TicketResolution:
        ticket = get_ticket(ticket_id)
        order = get_order(ticket["order_id"])

        thread = format_thread(ticket)
        snapshot = json.dumps(order, separators=(",", ":"))

        # Node 1: Triage — the only LLM call
        triage = self._triage(ticket_id, thread, snapshot)

        # Node 2: Retrieve — load the relevant KB article
        retrieved = self._retrieve(triage)

        # Node 3: Compose — construct the final resolution locally
        draft = self._compose(triage, retrieved)

        # Node 4: Audit — validate the final resolution
        final = self._audit(draft, retrieved)

        parsed = parse_resolution(final)

        return TicketResolution(
            action=parsed.action,
            kb_article=parsed.kb_article,
        )

    def _triage(self, ticket_id: str, thread: str, snapshot: str) -> str:
        messages = [
            ChatMessage(
                "system",
                "Triage the support request. Return JSON with "
                "action and kb_article.",
            ),
            ChatMessage(
                "user",
                f"TICKET:{ticket_id}\n"
                f"THREAD:{thread}\n"
                f"ORDER_SNAPSHOT:{snapshot}\n"
                "END_SNAPSHOT",
            ),
        ]

        return self.llm.chat("triage", messages)

    def _retrieve(self, triage: str) -> str:
        result = parse_resolution(triage)
        article = load_article(result.kb_article)

        if not article:
            raise ValueError(
                f"Knowledge-base article not found: {result.kb_article}"
            )

        return json.dumps(
            {
                "article_id": result.kb_article,
                "article": article,
            },
            separators=(",", ":"),
        )

    def _compose(self, triage: str, retrieved: str) -> str:
        triage_result = parse_resolution(triage)
        policy = json.loads(retrieved)

        if triage_result.kb_article != policy["article_id"]:
            raise ValueError(
                "Triage decision does not match the retrieved KB article."
            )

        # Build the final structured resolution without another LLM call.
        return json.dumps(
            {
                "action": triage_result.action,
                "kb_article": policy["article_id"],
            },
            separators=(",", ":"),
        )

    def _audit(self, draft: str, retrieved: str) -> str:
        result = parse_resolution(draft)
        policy = json.loads(retrieved)

        valid_actions = {
            "REFUND",
            "REPLACE",
            "SEND_ARTICLE",
            "ESCALATE_TIER2",
        }

        if result.action not in valid_actions:
            raise ValueError(f"Invalid action: {result.action}")

        if result.kb_article != policy["article_id"]:
            raise ValueError(
                "Final resolution does not match the retrieved KB article."
            )

        return draft