"""Checks score_contact against the answer key, without calling HubSpot.

Run from the flowdesk folder with:  python -m tests.test_scoring
"""

from shared.scoring import score_contact

# Each case: (who, the properties HubSpot would send, the score we expect)
CASES = [
    ("Amara", {"jobtitle": "Head of Marketing", "company": "Brightpath Logistics",
               "fd_company_size": "250", "fd_utm_campaign": "oct-launch"}, 100),
    ("Daniel", {"jobtitle": "Marketing Director", "company": "Kora Health",
                "fd_company_size": "45", "fd_utm_campaign": None}, 85),
    ("Sara", {"jobtitle": "HEAD OF GROWTH", "company": "Vela Finance",
              "fd_company_size": "60", "fd_utm_campaign": "oct-launch"}, 100),
    ("Grace", {"jobtitle": "Co-Founder", "company": "Lee & Co Bakery",
               "fd_company_size": "3", "fd_utm_campaign": None}, 55),
    ("Chidi", {"jobtitle": "Operations Manager", "company": "Northwind Retail",
               "fd_company_size": "1200", "fd_utm_campaign": None}, 45),
    ("Funmi", {"jobtitle": "Marketing Executive", "company": "Pebble Studio",
               "fd_company_size": "10", "fd_utm_campaign": "oct-launch"}, 60),
    ("Tom", {"jobtitle": None, "company": None,
             "fd_company_size": None, "fd_utm_campaign": None}, 0),
    ("Junk size", {"jobtitle": "Founder", "company": "Acme",
                   "fd_company_size": "about fifty", "fd_utm_campaign": None}, 55),
]


def main():
    passed = 0
    for who, props, expected in CASES:
        actual = score_contact(props)
        if actual == expected:
            passed += 1
            print(f"PASS  {who:<10} expected {expected:>3}, got {actual:>3}")
        else:
            print(f"FAIL  {who:<10} expected {expected:>3}, got {actual:>3}  <-- look here")
    print(f"\n{passed} of {len(CASES)} passed")


if __name__ == "__main__":
    main()