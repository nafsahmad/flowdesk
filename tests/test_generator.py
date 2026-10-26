"""Runs the whole generator with the fake model, on a good brief and the trap brief,
and checks the repair loop with a model that gets it wrong the first time.

Run from the flowdesk folder with:  python -m tests.test_generator
"""

import json
import os

os.environ["FLOWDESK_FAKE_LLM"] = "1"  # never call Bedrock from tests

from shared import generator, llm  # noqa: E402
from shared.generator import PROMPT_VERSIONS, extract_json, generate  # noqa: E402
from shared.prompts import brief_values  # noqa: E402


def load_brief(name):
    with open(f"sample_data/briefs/{name}.json", encoding="utf-8") as f:
        return json.load(f)


def test_repair_loop():
    """A model whose first blog is too short, and whose second is fine."""
    replies = iter([
        json.dumps({"title": "Short one", "body": "Too short. Book a 15-minute demo: {link}"}),
        json.dumps({"title": "Long one", "body": llm.FAKE_BLOG_BODY}),
    ])
    sent = []

    def fake_ask(system_prompt, user_prompt, **kwargs):
        sent.append(user_prompt)
        return next(replies)

    original = llm.ask
    llm.ask = fake_ask
    try:
        reply, checks, repairs = generator.write_and_repair(
            "rules", "Write a blog.", ["title", "body"],
            lambda b: {"blog": generator.check_blog(b["title"], b["body"])})
    finally:
        llm.ask = original
    return (repairs == 1 and reply["title"] == "Long one"
            and "word_count" in sent[1] and "Too short." in sent[1])


def main():
    checks = []

    good = generate(load_brief("onboarding-checklist"))
    checks.append(("Good brief ends as checked", good["status"] == "checked"))
    checks.append(("Good brief was judged 3 times", len(good["judge"]) == 3))
    checks.append(("Record says which model and prompts", good["model"] == "fake"
                   and good["prompt_versions"] == PROMPT_VERSIONS))
    checks.append(("No repairs needed for good fake copy",
                   good["repairs"] == {"blog": 0, "captions": 0}))
    checks.append(("{link} is still in the blog for later",
                   "{link}" in good["blog"]["body"]))

    risky = generate(load_brief("results-promise"))
    checks.append(("Trap brief ends as failed_checks", risky["status"] == "failed_checks"))
    checks.append(("Code check caught the made-up claim before the judge",
                   "agencies using flowdesk" in risky["rule_checks"]["blog"]["claim_phrases"]))

    verdict = generator.judge("rules", brief_values(load_brief("results-promise")),
                              "FlowDesk makes your team 3x faster.", "a blog post")
    checks.append(("Judge flags a made-up claim the code doesn't know",
                   verdict["made_up_claims"] == "yes"))
    clean = {"on_brand": 5, "matches_brief": 5, "platform_fit": 4,
             "made_up_claims": "no", "claims": []}
    flagged = {**clean, "made_up_claims": "yes", "claims": ["You get updates"]}
    poor = {**flagged, "on_brand": 2}
    
    checks.append(("Clean verdicts give checked",
                   generator.overall_status(True, {"blog": clean}) == "checked"))
    checks.append(("Flagged claims with decent scores give needs_review",
                   generator.overall_status(True, {"blog": flagged}) == "needs_review"))
    checks.append(("A score under 3 still fails",
                   generator.overall_status(True, {"blog": poor}) == "failed_checks"))

    checks.append(("Repair loop fixes a short blog, sending the reasons back",
                   test_repair_loop()))
    checks.append(("JSON inside ``` fences is read",
                   extract_json('```json\n{"a": 1}\n```') == {"a": 1}))
    checks.append(("Garbage gives None, not a crash", extract_json("sorry, no") is None))

    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{sum(ok for _, ok in checks)} of {len(checks)} passed")


if __name__ == "__main__":
    main()