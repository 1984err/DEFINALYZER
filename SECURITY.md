# Security and data handling

DEFINALYZER is a local, single-user research tool, not a hardened multi-user
service. Do not expose its dashboard through port forwarding or a public proxy.

## Local and external data

- The dashboard binds to loopback, validates request hosts, and requires a
  session token and same-origin browser requests for changes.
- Local applications running as your user are within the trust boundary. The
  dashboard is not a sandbox against malicious software on the same computer.
- Crawling contacts the supplied websites. AI actions send selected documents,
  questions, and evidence to the configured inference provider through Hermes.
- RPC and CoinGecko requests contact those external providers. The blockchain
  collector is read-only and does not require wallet seed phrases or keys.
- Keep credentials in the ignored `.env` or the provider's own configuration.
  Do not put secrets in prompts, research documents, or example files.
- `output/`, virtual environments, local planning files, logs, and common key
  files are ignored. Git ignores do not remove files already in Git history.

## Dependency maintenance

Install from `requirements.txt` and keep the installer current:

```text
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

The requirements include security floors for crawler dependencies. These are
not a guarantee against future advisories; review dependency updates regularly
and rerun the tests after changing them.

### Known upstream limitation (2026-09-03)

NLTK 3.10.3 remains affected by
[GHSA-8mgp-746c-j5xp](https://osv.dev/vulnerability/GHSA-8mgp-746c-j5xp),
concerning model-artifact APIs bypassing path restrictions. The advisory lists
no fixed release at this review. NLTK is a crawler dependency; its presence does
not establish exploitability in this application's workflow. Do not load
untrusted model/corpus artifacts or treat their path restrictions as a sandbox.
Reassess when an upstream fix is available.

## Before publishing

- Review the exact staged files, not just `.gitignore`.
- Scan for credentials, personal paths, real research, and image metadata.
- Check reachable Git history when assessing past disclosures. Deleting a file
  in a new commit does not erase earlier versions. Rotate exposed credentials;
  history rewriting requires coordination and does not retract existing clones.
- Run the release checks in README.md. Tests and scans reduce risk but are not
  a penetration test or a guarantee that all vulnerabilities have been found.

Do not publish exploit details or credentials in public issues. Use private
GitHub vulnerability reporting if available, or contact the maintainer privately.
