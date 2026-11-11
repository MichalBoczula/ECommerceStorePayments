"""Publish Payments verification for the exact Web consumer publication."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

from pact_registry import REPOSITORY, PactRegistry

SOURCE = Path(__file__).resolve().parents[1] / "contracts/pact/web-source.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()

    if os.environ["GITHUB_EVENT_NAME"] != "push" or os.environ["GITHUB_REF"] != "refs/heads/main":
        raise ValueError("Registry publication requires a Payments main push.")

    source = json.loads(SOURCE.read_bytes())
    report = json.loads(args.report.read_bytes())
    sha = os.environ["GITHUB_SHA"]
    digest = source["contractSha256"]
    if (report["consumerCommitSha"], report["providerCommitSha"], report["contractSha256"]) != (
        source["commitSha"],
        sha,
        digest,
    ):
        raise ValueError("The provider report does not match the pinned Pact and workflow commit.")

    call = PactRegistry().call
    publication_id = str(UUID(source["publicationId"]))
    publication = call(f"/api/contract-publications/{publication_id}")
    expected_publication = {
        "id": publication_id,
        "artifactSha256": digest,
        "kind": "ConsumerPact",
        "sourceApplicationId": "web",
        "consumerApplicationId": "web",
        "providerApplicationId": "payments",
        "commitSha": source["commitSha"],
        "sourceRef": "refs/heads/master",
        "buildUrl": f"https://github.com/{source['repository']}/actions/runs/{source['workflowRunId']}",
    }
    if any(publication.get(key) != expected for key, expected in expected_publication.items()):
        raise RuntimeError("The Web registry publication does not match the pinned source.")
    if hashlib.sha256(call(f"/api/artifacts/{digest}/content", raw=True)).hexdigest() != digest:
        raise RuntimeError("Registry artifact bytes differ from the verified Pact.")

    run = os.environ["GITHUB_RUN_ID"]
    build_url = f"{REPOSITORY}/actions/runs/{run}"
    call("/api/applications/payments/versions", {"commitSha": sha, "repositoryUrl": REPOSITORY})
    receipt = call(
        "/api/verification-runs",
        {
            **report,
            "consumerPublicationId": publication_id,
            "consumerApplicationId": "web",
            "providerApplicationId": "payments",
            "ciRunId": run,
            "ciAttempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
            "ciCheckId": "web-payments-lookup",
            "sourceRef": "refs/heads/main",
            "buildUrl": build_url,
            "evidenceUrls": [build_url],
        },
    )
    if (
        receipt["consumerPublicationId"] != publication_id
        or receipt["providerCommitSha"] != sha
        or receipt["contractSha256"] != digest
        or receipt["status"] != report["status"]
    ):
        raise RuntimeError("The registry returned a different verification result.")
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Published Payments verification {receipt['id']} ({receipt['status']}).")


if __name__ == "__main__":
    main()
