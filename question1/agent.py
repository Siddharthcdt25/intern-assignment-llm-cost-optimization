
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from shared.billing import CostSession
from shared.kb import load_article
from shared.llm import ChatMessage, LlmClient
from shared.tools import format_thread, get_order, get_ticket


@dataclass
class TicketResolution:
    action: str
    kb_article: str
    customer_reply: str
    raw_completion: str


def parse_resolution(text: str) -> TicketResolution:
    m = re.search(r"\{[\s\S]*\}", text)

    if not m:
        raise ValueError(f"No JSON in model output:\n{text[:400]}")

    data = json.loads(m.group())

    return TicketResolution(
        action=str(data["action"]).upper(),
        kb_article=str(data["kb_article"]),
        customer_reply=str(data.get("customer_reply", "")),
        raw_completion=text,
    )


def select_relevant_article(order: dict) -> str:
    """
    Select the relevant help-center article using order attributes.
    This avoids sending the entire knowledge base to the LLM.
    """

    product_type = order.get("product_type", "").lower()

    if product_type == "subscription":
        return "subscription-cooling-off"

    if product_type == "digital" or order.get("license_revealed"):
        return "digital-license-no-refund"

    if product_type == "custom" or order.get("customized"):
        return "custom-items-no-replace"

    if (
        order.get("damage_reported")
        and order.get("delivered_days_ago", 999) <= 7
    ):
        return "damage-replacement-7-days"

    if (
        product_type == "physical"
        and order.get("delivered_days_ago", 999) <= 30
    ):
        return "returns-within-30-days"

    return "returns-within-30-days"


class SupportCopilot:
    """
    Optimized ShopAssist Tier-1 support copilot.
    Uses one LLM call per ticket with a compact policy context.
    """

    def __init__(self, session: CostSession | None = None):
        self.session = session or CostSession()
        self.llm = LlmClient(self.session)

    def build_messages(self, ticket_id: str) -> list[ChatMessage]:

        ticket = get_ticket(ticket_id)
        order = get_order(ticket["order_id"])

        thread = format_thread(ticket)
        snapshot = json.dumps(order, separators=(",", ":"))

        article_id = select_relevant_article(order)
        article_content = load_article(article_id)

        system = (
            "You are ShopAssist, a Tier-1 customer support copilot.\n"
            "Resolve the customer request using the supplied order facts "
            "and relevant help-center policy.\n"
            f"RELEVANT POLICY ({article_id}):\n"
            f"{article_content}\n"
            "Return only valid JSON with these fields: "
            "action, kb_article, customer_reply."
        )

        user = (
            f"TICKET_ID: {ticket_id}\n"
            f"THREAD:\n{thread}\n"
            f"ORDER_SNAPSHOT:\n{snapshot}\n"
            "END_SNAPSHOT"
        )

        return [
            ChatMessage("system", system),
            ChatMessage("user", user),
        ]

    def handle_ticket(self, ticket_id: str) -> TicketResolution:

        messages = self.build_messages(ticket_id)

        completion = self.llm.chat("handle_ticket", messages)

        return parse_resolution(completion)
