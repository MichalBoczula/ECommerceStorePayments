"""Publish the exact Payments CI Pact bytes with consumer-scoped credentials."""

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path

from pact_registry import REPOSITORY, PactRegistry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("commit")
    parser.add_argument("run_id")
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit) or not re.fullmatch(r"[0-9]+", args.run_id):
        raise ValueError("Expected a full source commit SHA and numeric GitHub run ID.")

    post = PactRegistry().call

    manifest = json.loads((args.artifact / "manifest.json").read_bytes())
    content = (args.artifact / "payments-invoice.json").read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    pact = json.loads(content)
    if (
        manifest["schemaVersion"] != 1
        or manifest["file"] != "payments-invoice.json"
        or manifest["sha256"] != digest
        or (manifest["consumer"], pact["consumer"]["name"], manifest["provider"], pact["provider"]["name"])
        != ("payments", "payments", "invoice", "invoice")
        or manifest["pactSpecification"] != "4.0"
        or pact["metadata"]["pactSpecification"]["version"] != "4.0"
        or manifest["interactionCount"] != len(pact["interactions"])
    ):
        raise ValueError("Artifact bytes or Pact identity differ from the Payments manifest.")

    post("/api/applications/payments/versions", {"commitSha": args.commit, "repositoryUrl": REPOSITORY})
    post("/api/integrations", {"consumerApplicationId": "payments", "providerApplicationId": "invoice"})
    build_url = f"{REPOSITORY}/actions/runs/{args.run_id}"
    publication = post(
        "/api/contract-publications",
        {
            "sourceApplicationId": "payments",
            "commitSha": args.commit,
            "kind": "ConsumerPact",
            "consumerApplicationId": "payments",
            "providerApplicationId": "invoice",
            "sourceRef": "refs/heads/main",
            "buildUrl": build_url,
            "contentBase64": base64.b64encode(content).decode("ascii"),
        },
    )
    if publication["artifactSha256"] != digest:
        raise RuntimeError("The registry returned a different artifact hash.")
    args.receipt.write_text(
        json.dumps(
            {"publicationId": publication["id"], "commitSha": args.commit, "sha256": digest, "buildUrl": build_url}
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Published Payments Pact {digest} as {publication['id']}.")


if __name__ == "__main__":
    main()
