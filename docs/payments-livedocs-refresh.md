# Manual LiveDocs refresh — audited Payments BDD

Use the frozen, archived Payments input below. It has passed the
[final audit](bdd-16-final-audit.md), including all **391 BDD cases, seventeen
features and 21,242 rendered attachments**. Main
[run 41053783581](https://github.com/MichalBoczula/ECommerceStorePayments/actions/runs/41053783581)
is successful, including service-image publication and documentation archival.
The `documentation-reference` artifact is the exact source of this reference.
Later producer runs create separate candidates; do not silently substitute one
without its own audit.

## Exact manifest reference

In **ECommerceStore.LiveDocs**, update only project `payments` in the existing
**development v1** entry of `manifests/portal.json` with this object:

```json
{
  "project": "payments",
  "commitSha": "bebd01803175b442453c31403ddd2f58f1790cc8",
  "generatedAt": "2026-10-30T12:27:08Z",
  "workflowRunId": 41053783581,
  "artifact": {
    "url": "https://stecproductsdevmb261013.blob.core.windows.net/livedocs/reports/payments/bebd01803175b442453c31403ddd2f58f1790cc8/deaafa169451d60066f888b3f0130ec314c010961cb848d7604275f2294e1b82.zip",
    "sha256": "deaafa169451d60066f888b3f0130ec314c010961cb848d7604275f2294e1b82",
    "sizeBytes": 26035978
  }
}
```

The receipt is also archived at:

`candidates/v1/payments/41053783581-deaafa169451d60066f888b3f0130ec314c010961cb848d7604275f2294e1b82.json`

At audit time, the manifest still selects the original 51-case Payments snapshot
from run `40219243830`, source `ab868c98940741ef6422dfafcab71134f3e4b8e3`.
This handoff does not edit that repository or alter a running report.

## Review, publish and deploy

1. Read the current LiveDocs manifest before editing. Retain all other project
   references and retained versions, including Products, Users and Orders/Invoices.
   Replace only the Payments object above; keep `latestVersion` and development
   version selection unchanged. Do not edit a released version.
2. Open a LiveDocs manifest PR. Require the existing private-prefetch gate to
   download the exact archived URL and verify its digest, size, inventory,
   source identity and attachments. Then require actual Allure generation,
   production-container HTTP checks, image scanning and the full LiveDocs gate.
   A missing archive or failed check blocks selection. Existing reader-secret
   and protected-environment rules apply; no credentials belong in the manifest.
3. After that PR is reviewed and merged, require LiveDocs main CI to publish the
   same tested/scanned image. Record the LiveDocs commit and immutable image
   digest from its `livedocs-image/image.json` artifact/publication summary.
   The Payments API image digest is not the LiveDocs deployment image.
4. In **ECommerceStore.Terraform**, update only `app_images.livedocs` to that
   LiveDocs image digest, retaining all other images and the existing shared
   root/state. Review a fresh plan and apply it manually:

   ```powershell
   terraform plan "-out=livedocs.tfplan"
   terraform apply livedocs.tfplan
   $liveDocsUrl = (terraform output -json app_urls | ConvertFrom-Json).livedocs
   Invoke-RestMethod "$liveDocsUrl/health/ready" -TimeoutSec 180
   Invoke-RestMethod "$liveDocsUrl/build-info.json" -TimeoutSec 180
   Start-Process "$liveDocsUrl/livedoc/v1/payments/"
   Start-Process "$liveDocsUrl/livedoc/v1/payments/allure/"
   ```

5. Compare `build-info.json.commitSha` with the **LiveDocs** image commit. Check
   `/livedoc/catalog.json` and the Payments page show the **Payments** source/run/
   digest above, all 391 passed cases, seventeen features and the new source/evidence
   attachments. Open API/flow/policy JSON links, native tables, representative
   HTTP/action evidence and Invoice PDF downloads. Confirm Products, Users and
   Orders/Invoices pages remain available. Host readiness alone is not proof of
   a selected report or successful BDD execution.

A source upload does not refresh the deployed report. Retain the selected archive
and receipt without blanket expiry. This needs no new Azure resource, runtime
Blob connection, Stripe configuration or automatic importer. **PAY/21** closes
only after the separate selection/image/deployment checks above succeed.

The procedure follows the current
[LiveDocs producer integration](https://github.com/MichalBoczula/ECommerceStore.LiveDocs/blob/main/docs/producer-integration.md)
and [container contract](https://github.com/MichalBoczula/ECommerceStore.LiveDocs/blob/main/docs/container-contract.md).
