"""Generate synthetic workshop dataset (GDPR-safe) for intake + RAG demos.

Usage:
  python scripts/demo/generate_dataset.py --out docs/samples/generated --count 60
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

VENDORS = ["Contoso", "Northwind", "Fabrikam", "Woodgrove", "Alpine"]
INCIDENTS = [
    "phishing email requesting MFA reset",
    "laptop lost on train",
    "VPN outage impacting remote workers",
    "malware alert from endpoint tool",
    "suspicious login from unknown country",
]
POLICIES = [
    "Password Rotation Policy",
    "Incident Response Playbook",
    "Remote Work Security Standard",
    "Data Retention and Deletion Policy",
    "Vendor Access Control Policy",
]


def make_invoice(i: int) -> str:
    vendor = random.choice(VENDORS)
    amount = random.randint(120, 9800)
    due = random.choice([7, 14, 21, 30])
    return (
        f"Invoice INV-{1000+i} from {vendor} for EUR {amount}.00 due in {due} days. "
        f"Reference PO-{5000+i}."
    )


def make_incident(i: int) -> str:
    incident = random.choice(INCIDENTS)
    mins = random.choice([10, 20, 35, 50])
    return (
        f"Incident report IR-{2000+i}: Employee reported {incident}. "
        f"Initial containment started within {mins} minutes."
    )


def make_policy(i: int) -> str:
    policy = random.choice(POLICIES)
    return (
        f"{policy} (v{i%5+1}): Staff must report suspected phishing to IT Service Desk within 1 hour. "
        f"Use approved channels and preserve evidence."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/samples/generated")
    ap.add_argument("--count", type=int, default=60)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for i in range(args.count):
        kind = ["invoice", "incident", "policy"][i % 3]
        if kind == "invoice":
            text = make_invoice(i)
        elif kind == "incident":
            text = make_incident(i)
        else:
            text = make_policy(i)

        p = out / f"{kind}-{i:03}.txt"
        p.write_text(text + "\n", encoding="utf-8")

    print(f"Generated {args.count} files in {out}")


if __name__ == "__main__":
    main()
