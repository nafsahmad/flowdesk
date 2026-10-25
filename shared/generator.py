"""Turns a brief into checked drafts: a blog post and captions A and B.

Flow: fill the prompts, ask the model, read its JSON, run the rule checks.
If a rule fails, send the draft back once with the exact problems (the repair
loop). Only if every rule passes does the judge run. Returns one record with
everything, including how it was made.
"""

import json
from datetime import datetime, timezone

from shared import llm
from shared.checks import check_blog, check_copy, passed
from shared.prompts import brief_values, fill, load

PROMPT_VERSIONS = {"blog": "v3", "caption": "v3", "judge": "v1"}
MIN_JUDGE_SCORE = 4
MAX_REPAIRS = 1


class GenerationError(Exception):
    """The model didn't give us something we could use."""


def extract_json(reply):
    """Pull the JSON object out of a reply, even if it's wrapped in ``` fences."""
    start, end = reply.find("{"), reply.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(reply[start:end + 1])
    except json.JSONDecodeError:
        return None


def ask_for_json(system_prompt, user_prompt, required_keys):
    """Ask the model, and try once more if the reply isn't usable JSON."""
    for _attempt in range(2):
        data = extract_json(llm.ask(system_prompt, user_prompt))
        if data is not None and all(key in data for key in required_keys):
            return data
    raise GenerationError(f"No usable JSON with keys {required_keys} after 2 tries")


def failures(checks_by_piece):
    """Turn failed checks into plain sentences the model can act on."""
    return [f"{piece}, {check}: {reason}"
            for piece, checks in checks_by_piece.items()
            for check, reason in checks.items() if reason != "pass"]


def repair_prompt(original_prompt, previous_reply, problems):
    """The original task, the model's last attempt, and exactly what was wrong."""
    return (original_prompt
            + "\n\nYour previous reply was:\n" + json.dumps(previous_reply)
            + "\n\nIt broke these rules:\n" + "\n".join(f"- {p}" for p in problems)
            + "\n\nRewrite it so every problem above is fixed, and keep everything that "
              "was already right. Reply with JSON only, in the same shape.")


def write_and_repair(brand_rules, prompt, keys, run_checks):
    """Ask, check, and if any rule fails, ask once more with the problems listed.

    Returns (reply, checks, number of repairs used).
    """
    reply = ask_for_json(brand_rules, prompt, keys)
    checks = run_checks(reply)
    repairs = 0
    while failures(checks) and repairs < MAX_REPAIRS:
        repairs += 1
        reply = ask_for_json(brand_rules, repair_prompt(prompt, reply, failures(checks)), keys)
        checks = run_checks(reply)
    return reply, checks, repairs


def judge(brand_rules, values, copy, platform):
    """Ask the judge to score one piece of copy."""
    prompt = fill(load(f"judge_{PROMPT_VERSIONS['judge']}.txt"),
                  {**values, "brand_rules": brand_rules, "copy": copy,
                   "platform": platform})
    return ask_for_json("You are a strict, fair marketing editor.", prompt,
                        ["on_brand", "matches_brief", "platform_fit", "made_up_claims"])


def judge_passed(verdict):
    scores_ok = all(verdict[k] >= MIN_JUDGE_SCORE
                    for k in ("on_brand", "matches_brief", "platform_fit"))
    return scores_ok and verdict["made_up_claims"] == "no"


def generate(brief):
    """Run the whole flow for one brief. Returns the record to save."""
    brand_rules = load("brand_rules.md")
    values = brief_values(brief)

    blog, blog_checks, blog_repairs = write_and_repair(
        brand_rules,
        fill(load(f"blog_{PROMPT_VERSIONS['blog']}.txt"), values),
        ["title", "body"],
        lambda b: {"blog": check_blog(b["title"], b["body"])},
    )
    captions, caption_checks, caption_repairs = write_and_repair(
        brand_rules,
        fill(load(f"caption_{PROMPT_VERSIONS['caption']}.txt"), values),
        ["A", "B"],
        lambda c: {"caption_A": check_copy(c["A"], 40, 80, social=True),
                   "caption_B": check_copy(c["B"], 40, 80, social=True)},
    )

    rule_checks = {**blog_checks, **caption_checks}
    rules_ok = all(passed(r) for r in rule_checks.values())

    verdicts = {}
    if rules_ok:  # the judge costs money, so only judge copy that passed the free checks
        verdicts = {
            "blog": judge(brand_rules, values, blog["body"], "a blog post"),
            "caption_A": judge(brand_rules, values, captions["A"], "a LinkedIn caption"),
            "caption_B": judge(brand_rules, values, captions["B"], "a LinkedIn caption"),
        }
    judge_ok = bool(verdicts) and all(judge_passed(v) for v in verdicts.values())

    return {
        "brief_id": brief["brief_id"],
        "status": "checked" if rules_ok and judge_ok else "failed_checks",
        "model": llm.model_name(),
        "prompt_versions": PROMPT_VERSIONS,
        "repairs": {"blog": blog_repairs, "captions": caption_repairs},
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "blog": blog,
        "captions": captions,
        "rule_checks": rule_checks,
        "judge": verdicts,
    }