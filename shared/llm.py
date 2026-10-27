"""The one place FlowDesk talks to a language model.

Set the environment variable FLOWDESK_FAKE_LLM=1 to get ready-made replies
instead of calling Bedrock. Everything else calls ask() and never knows which.
"""

import json
import os

MODEL_ID = os.environ.get("FLOWDESK_MODEL_ID", "eu.amazon.nova-2-lite-v1:0")
REGION = "eu-north-1"


def using_fake():
    return os.environ.get("FLOWDESK_FAKE_LLM") == "1"


def model_name():
    """What to record as the model in each draft."""
    return "fake" if using_fake() else MODEL_ID


def ask(system_prompt, user_prompt, max_tokens=2000, temperature=0.7):
    """Send one prompt and return the model's reply as text."""
    if using_fake():
        return _fake_reply(user_prompt)

    import boto3  # only needed when calling the real Bedrock

    client = boto3.client("bedrock-runtime", region_name=REGION)
    try:
        response = client.converse(
            modelId=MODEL_ID,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
    except Exception as e:
        raise RuntimeError(
            f"Bedrock call failed (model {MODEL_ID!r}, region {REGION!r}): {e}"
        ) from e
    blocks = response["output"]["message"]["content"]
    return "".join(block.get("text", "") for block in blocks)


# ---------------------------------------------------------------------------
# The fake model. It recognises which prompt it was sent and replies in the
# same JSON shape Bedrock would. If the brief pushes for "results", it invents
# one on purpose, so the judge has something to catch.
# ---------------------------------------------------------------------------

FAKE_BLOG_BODY = (
    "Every agency knows the feeling. A new client signs, everyone is excited, and "
    "then week one turns into a chase. Someone needs the contract back. Someone else "
    "needs the intake form. The ads team is still waiting for account access, and "
    "the kickoff call keeps moving.\n\n"
    "None of this is hard work. It's just scattered work. The details live in email "
    "threads, shared drives and a project manager's memory, so they slip. When they "
    "slip, the client's first impression is a string of reminder emails instead of "
    "real progress on their marketing.\n\n"
    "The fix is less exciting than a new tool for every step. It's one checklist that "
    "every new client moves through in the same order, every time.\n\n"
    "That's what FlowDesk does. FlowDesk sends clients one link where they sign the "
    "contract, fill in the intake form and share account access. Your team doesn't "
    "build the list from scratch for each client either. Agencies reuse the same "
    "onboarding template for every new client, so the process gets better each time "
    "you refine it instead of starting over.\n\n"
    "The chasing goes too. FlowDesk reminds clients automatically when something is "
    "still missing, so your account managers can spend week one on strategy and "
    "relationships rather than follow-up emails.\n\n"
    "If your agency has between five and fifty people, onboarding is probably handled "
    "by whoever has a spare hour. A shared checklist means it no longer depends on one "
    "person remembering everything. New staff can run it on day one, and clients see "
    "a calm, organised agency from the very first link they open.\n\n"
    "Start with the client you're onboarding next and see how much quieter the first "
    "week feels.\n\n"
    "Book a 15-minute demo: {link}"
)
FAKE_CLAIM = "Agencies using FlowDesk onboard clients 3x faster. "

FAKE_CAPTION_A = (
    "New clients are exciting until week one turns into a chase for contracts, "
    "forms and logins. FlowDesk sends each client one link where they sign, fill in "
    "the intake form and share access. Your team gets one checklist that fills itself "
    "in, and clients get reminded automatically when something is missing. "
    "Book a 15-minute demo: {link}"
)
FAKE_CAPTION_B = (
    "Week one with a new client can be calm. The contract is signed, the intake "
    "form is done and access is shared, all from one link. "
    "FlowDesk reminds clients automatically when something is still missing, and "
    "your team reuses the same template for every new client. "
    "Book a 15-minute demo: {link}"
)

FAKE_SUMMARY = (
    "The ad spend in this report is sample data.\n\n"
    "What happened\nLeads arrived from both caption variants.\n\n"
    "What worked\nBoth variants produced leads.\n\n"
    "What failed\nSome leads arrived without a variant.\n\n"
    "What should happen next\nShare only tracked links. Keep testing both variants."
)

def _fake_reply(prompt):
    if "weekly marketing assessment" in prompt:
        return FAKE_SUMMARY
    risky = "Mention the results" in prompt
    if "Score each from 1" in prompt:
        copy = prompt.split("The copy to review:", 1)[-1]
        if "3x" in copy:
            return json.dumps({"on_brand": 3, "matches_brief": 4, "platform_fit": 4,
                               "made_up_claims": "yes",
                               "claims": ["onboard clients 3x faster"]})
        return json.dumps({"on_brand": 5, "matches_brief": 5, "platform_fit": 4,
                           "made_up_claims": "no", "claims": []})
    if '{"A":' in prompt:
        a = (FAKE_CLAIM + FAKE_CAPTION_A) if risky else FAKE_CAPTION_A
        return json.dumps({"A": a, "B": FAKE_CAPTION_B})
    body = (FAKE_CLAIM + FAKE_BLOG_BODY) if risky else FAKE_BLOG_BODY
    return "```json\n" + json.dumps({"title": "One checklist for every new client",
                                     "body": body}) + "\n```"