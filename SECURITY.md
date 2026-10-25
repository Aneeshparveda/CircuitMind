# Security — CircuitMind

CircuitMind is a local, offline prototype. It runs as a Streamlit app on
your own machine, has no networked service, no user accounts, and no
API keys at diagnosis time. Files you upload in the app (test-log CSVs,
up to 5 MB) are processed locally and are not sent anywhere by the app.

## Reporting a vulnerability

Please report security issues through a GitHub Issue in this
repository, or by email to Aneesh Parveda at aneeshparveda@gmail.com.
Do not include real proprietary factory data, credentials, or personal
information in a public issue — use synthetic or redacted examples.

## Scope notes

- This is a hackathon prototype, not a production factory tool. Do not
  rely on it for safety-critical or production repair decisions.
- Dependencies are listed in `requirements.txt`; keep them pinned when
  changing versions, and say why a version changed.
