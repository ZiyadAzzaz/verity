# Security policy

## Reporting a vulnerability

Please do not disclose an exploitable vulnerability in a public Issue or in
`verity-reports`. Use GitHub's private vulnerability reporting for this repository. If that
option is unavailable, contact the repository owner privately through the contact method on the
owner's GitHub profile.

Include the affected component, reproduction steps, impact, and any relevant non-secret logs.
Never include API keys, access tokens, identity tokens, secret values, or private user data.

## Security model

Verity deliberately separates trusted orchestration from untrusted benchmark execution:

- the public service requires a managed API key for job submission and job reads;
- Pub/Sub invokes the private worker using audience-bound Google OIDC;
- application and GitHub credentials come from Google Secret Manager;
- untrusted code runs in a separate Cloud Run Job under a service account with no project roles;
- the sandbox receives no application secret or Google credential;
- evaluation has a bounded runtime and at most three transparent repair attempts;
- only the trusted pipeline persists state and files the final GitHub report.

A live pre-production probe attempted Firestore, Secret Manager, Pub/Sub, Cloud Run, Vertex AI,
and Cloud Storage access from the sandbox and recorded six explicit denials. The full design and
remaining limitations are documented in
[docs/SECURITY-QUALITY-REPORT.md](docs/SECURITY-QUALITY-REPORT.md).

## Supported version

Security fixes are applied to the latest commit on `main`. This is a hackathon project rather
than a versioned commercial service; older commits and historical diagnostic deployments are not
supported.
