# Verity Google Cloud Console Inspection Guide

- **Prepared:** 2026-08-27
- **Project:** `verity-506800`
- **Region:** `us-central1`
- **Expected account:** `ziyadazzazdesigner@gmail.com`
- **Purpose:** inspect the sandbox-probe state and cost without changing anything

This is the visual companion to
[WORKLOG-2026-08-27-CLOUD-SANDBOX-PREPARATION.md](WORKLOG-2026-08-27-CLOUD-SANDBOX-PREPARATION.md).
The worklog explains what was done, what failed, why each decision was made, test evidence, cost,
professional assessment, and the next approval gate. This guide shows exactly where to see the
same facts in Google Cloud Console.

## Critical safety rule

This is a **read-only inspection**. Do not click any control that creates, edits, executes,
publishes, grants, deletes, or changes financial configuration.

In particular, do **not** click:

- **Execute**, **Execute job**, **Deploy**, **Edit**, or **Delete** in Cloud Run;
- **Grant access**, **Edit principal**, or **Add role** in IAM;
- **Add new version**, **View secret value**, **Disable**, or **Destroy** in Secret Manager;
- **Publish message**, **Create subscription**, or **Delete topic** in Pub/Sub;
- **Run trigger**, **Rebuild**, or **Retry** in Cloud Build;
- **Budgets & alerts**, **Payment settings**, **Account management**, **Manage payment methods**,
  **Upgrade**, **Quota**, or any financial edit control.

If the Console displays an unexpected resource, nonzero sandbox IAM role, job execution, public
access, cost above `$0.01` for the recorded attempts, or the wrong project/account, stop and send
the details before changing anything.

## What the probe has done so far

```mermaid
flowchart LR
    S[Clean Git revision b3a3e0e] --> B[Default-pool Cloud Build<br/>60.914 seconds]
    B --> I[Immutable sandbox image<br/>SHA-256 digest]
    I --> J[Private verity-sandbox Job<br/>no-role service account]
    J -. not executed yet .-> P[Steal own metadata token]
    P -. pending .-> D[Six sensitive APIs<br/>must each deny 401/403]
    D -. pending .-> E[Final JSON evidence]
```

The solid path is complete. The dotted path has **not run**. The Console must currently show zero
Cloud Run Job executions and cannot yet show the six denial results.

## Step 1 — Confirm the account and project

1. Open the [Google Cloud project dashboard](https://console.cloud.google.com/home/dashboard?project=verity-506800).
2. Look at the account avatar in the top-right corner.
3. Confirm the signed-in account is `ziyadazzazdesigner@gmail.com`.
4. Look at the project selector in the top bar.
5. Confirm it says project ID `verity-506800`, not merely a similar display name.

Expected result:

- account: `ziyadazzazdesigner@gmail.com`;
- project ID: `verity-506800`; and
- project status: active.

Stop if either the account or project differs.

## Step 2 — Inspect actual Billing Reports safely

1. With `verity-506800` still selected, open
   [Cloud Billing](https://console.cloud.google.com/billing?project=verity-506800).
2. If Google asks which billing account to view, select the account linked to this project. Do not
   copy its identifier into public documentation.
3. In the left menu, choose **Reports**. Do not open or edit **Budgets & alerts**.
4. Set **Time range** to **Current month** or a custom range beginning `2026-08-27`.
5. Set the **Projects** filter to only `verity-506800`.
6. Set **Group by** to **Service**.
7. Record the values shown for:
   - total cost before credits;
   - credits/discounts;
   - net cost; and
   - the report's latest data timestamp.
8. If any cost appears, also group by **SKU** and record which SKU produced it.

Billing data can be delayed. If the report says `$0.00`, also record the latest data timestamp so
we know whether the build time is covered. If it shows no new data yet, report **not posted yet**,
not `$0.00 confirmed`.

Expected measured usage before billing discounts:

- Cloud Build default-pool list-price equivalent: approximately `$0.006091`;
- Artifact Registry: 179.128 MB, below the first 0.5 GiB-month free allowance;
- Secret Manager: one active version, below the first six-version allowance;
- Pub/Sub: zero throughput;
- Cloud Run compute: `$0.00`, because there are no executions; and
- conservative combined upper bound: less than `$0.01` plus negligible storage.

Official reference: [Google Cloud Billing Reports documentation](https://docs.cloud.google.com/billing/docs/how-to/reports).

## Step 3 — Inspect the successful Cloud Build

1. Open [Cloud Build history](https://console.cloud.google.com/cloud-build/builds?project=verity-506800).
2. Find build ID `65d041cb-3b3f-4422-b023-a9682cc266cc`.
3. Open it and verify:
   - status: **Success**;
   - start: `2026-08-27 09:04:09 UTC` approximately;
   - finish: `2026-08-27 09:05:10 UTC` approximately;
   - duration: approximately **1 minute 1 second**;
   - image tag ends in `verity-sandbox:b3a3e0e21f4e`; and
   - no private worker-pool name is shown.
4. You may read the build log. Do not click **Rebuild**, **Retry**, or create a trigger.

The source upload was 2,520,513 bytes. Cloud Build ID and duration are the primary evidence used
for the cost calculation.

## Step 4 — Inspect the immutable Artifact Registry image

1. Open [Artifact Registry](https://console.cloud.google.com/artifacts?project=verity-506800).
2. Select region `us-central1` if the page asks for a location.
3. Open repository `verity`.
4. Open package/image `verity-sandbox`.
5. Verify the revision tag is `b3a3e0e21f4e`.
6. Verify the digest is exactly:

   ```text
   sha256:a8dba0655a6c35f3dac2fa99818dae91319b915f8c28e252c7ddc8ebb50f9822
   ```

7. Confirm repository size is approximately **179.128 MB**.

Do not delete the image or change cleanup policies. The digest is important because a SHA-256
digest cannot silently move to a different container image the way a mutable tag can.

## Step 5 — Inspect the private Cloud Run Job

1. Open [Cloud Run Jobs](https://console.cloud.google.com/run/jobs?project=verity-506800).
2. Set region to `us-central1`.
3. Open job `verity-sandbox`.
4. On the job details/configuration tabs, confirm:
   - service account:
     `verity-sandbox@verity-506800.iam.gserviceaccount.com`;
   - image uses the exact SHA-256 digest from Step 4;
   - CPU: `2`;
   - memory: `4 GiB`;
   - task timeout: `3600 seconds`;
   - maximum retries: `0`;
   - environment variables: none;
   - secrets: none;
   - volumes and volume mounts: none; and
   - VPC/network attachment: none.
5. Open **Executions** or the execution-history section.
6. Confirm it contains **zero executions**.

Do not click **Execute**. The next execution must be launched only by the reviewed validator after
explicit approval. Google documents that a job execution starts container resources and appears
in the execution list: [Cloud Run execution documentation](https://docs.cloud.google.com/run/docs/managing/job-executions).

## Step 6 — Confirm the sandbox identity has no project role

1. Open [Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts?project=verity-506800).
2. Confirm the account
   `verity-sandbox@verity-506800.iam.gserviceaccount.com` exists.
3. Open [IAM](https://console.cloud.google.com/iam-admin/iam?project=verity-506800).
4. Use the filter field to search for the full sandbox service-account email.
5. Expected result: no direct project-level role is granted to this principal. Depending on the
   Console view, that can appear as no IAM row at all because principals with zero grants are not
   listed in the project policy.
6. If any role appears—especially Owner, Editor, Viewer, Cloud Run, Storage, Secret Manager,
   Pub/Sub, Vertex AI, or Firestore roles—stop and send the role name. Do not remove it yourself.

The command-line evidence also found zero resource-level IAM policies referencing this identity.
The Console project IAM view is a human-readable cross-check, not a replacement for the project
and resource-policy searches already recorded.

## Step 7 — Inspect the non-sensitive Secret Manager sentinel

1. Open [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=verity-506800).
2. Open `verity-sandbox-deny-probe`.
3. Confirm there is exactly one enabled version: version `1`.
4. Confirm automatic replication is used.

Do not view the value and do not add, disable, or destroy a version. The value is deliberately
non-sensitive, but inspecting it is unnecessary. Its purpose is only to prove later that the
sandbox token cannot read Secret Manager.

## Step 8 — Inspect the Pub/Sub sentinel topic

1. Open [Pub/Sub Topics](https://console.cloud.google.com/cloudpubsub/topic/list?project=verity-506800).
2. Open topic `verification-jobs`.
3. Confirm the full name is
   `projects/verity-506800/topics/verification-jobs`.
4. Confirm there is no production push subscription created by this probe.

Do not publish a message or create a subscription. The topic exists only so the sandbox token can
later attempt—and be denied—a real publish request.

## Step 9 — Inspect enabled APIs

1. Open the [APIs & Services dashboard](https://console.cloud.google.com/apis/dashboard?project=verity-506800).
2. Confirm the expected APIs are enabled, including Cloud Run, Cloud Build, Artifact Registry,
   Secret Manager, Pub/Sub, Firestore, Vertex AI, Cloud Storage, Cloud Asset, and Logging.

API enablement alone does not prove the API was used and does not prove the security check passed.
Do not enable additional APIs, change quota, or request quota increases.

## Step 10 — Optional Cloud Build source-storage check

1. Open [Cloud Storage browser](https://console.cloud.google.com/storage/browser?project=verity-506800).
2. Open bucket `verity-506800_cloudbuild` if it is visible.
3. Open folder `source/`.
4. The recorded source object is:

   ```text
   1787821437.85186-fac0c3a4a1aa4ec391dc16fb44b32da5.tgz
   ```

5. Its recorded size is **2,520,513 bytes**.

Do not delete it or change the bucket lifecycle during this inspection.

## Expected-state checklist

- [ ] Correct account and project are selected.
- [ ] Billing report is filtered only to `verity-506800` and its latest-data time is recorded.
- [ ] Build `65d041cb-3b3f-4422-b023-a9682cc266cc` shows Success and about 61 seconds.
- [ ] Repository `verity` contains the expected immutable sandbox digest.
- [ ] `verity-sandbox` Job is private and has zero executions.
- [ ] Sandbox service account exists with no project IAM role.
- [ ] Sentinel secret has exactly one active version.
- [ ] Sentinel Pub/Sub topic exists without a production push subscription.
- [ ] No Verity API, pipeline worker, or public production service exists.
- [ ] No setting was edited during inspection.

## Send these details back

Copy this template into your reply and fill in only what the Console visibly shows. Screenshots are
also useful, but hide billing-account IDs or unrelated project information.

```text
Project shown: verity-506800 / different
Billing report time range:
Billing latest-data timestamp:
Cost before credits:
Credits/discounts:
Net cost:
Services or SKUs with nonzero cost:
Cloud Build status and duration:
Artifact digest matches: yes/no
Cloud Run execution count:
Sandbox IAM roles shown:
Secret versions shown:
Pub/Sub subscriptions shown:
Anything unexpected:
```

## Professional assessment and what happens next

The current Console state should show a correctly built, digest-pinned, no-role sandbox job that
has never executed. That is a strong precondition, but it is not the security proof. The decisive
evidence is still one authorized execution whose stolen metadata token receives explicit `401` or
`403` from all six sensitive APIs.

After you inspect the pages and send the Billing/Console details, the recommended next step is to
authorize one new complete probe invocation. The agent will reconfirm the clean pushed revision,
run the validator once, preserve the exact JSON, measure the execution cost, update the Markdown
work record, and keep both production guards closed for your separate review.

## Documentation record

This guide was added because the technical worklog alone did not provide a simple visual Console
walkthrough. It adds no cloud resources and performs no cloud or billing mutation. Its design
intentionally separates inspection from action so a reviewer cannot accidentally turn evidence
collection into an unapproved deployment, IAM change, job execution, or financial change.
