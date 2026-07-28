# Verification Request Import

The importer translates an explicitly structured research request into the
existing collection-job schema. It validates and routes requests; it does not
choose a verification method, interpret evidence, or decide whether a claim is
true.

## Markdown contract

A research Markdown file must contain exactly one fenced block labelled
`definalyzer-verification`. Raw `.json` files may contain the same object
without a fence.

````text
```definalyzer-verification
{
  "schema_version": 1,
  "name": "unique-job-name",
  "requests": []
}
```
````

Each request must contain only these fields:

| Field | Required | Meaning |
|---|---:|---|
| `id` | Yes | Unique collector-compatible request name |
| `claim` | Yes | Claim context retained for a later evaluation step |
| `why_verify` | Yes | Why the claim materially affects analysis |
| `chain` | Yes | `ethereum`, `arbitrum`, or `base` |
| `operation` | Yes | One operation from the capability manifest |
| `parameters` | As required | Exact parameters accepted by that operation |
| `target` | By operation | Registry-derived address and provenance |

There is deliberately no verdict, expected result, interpretation, or
verified marker in this format.

Use the complete example at
`examples/verification_requests_example.md`.

## Import without running

```powershell
python -m blockchain_collector.verification_import `
  research.md `
  jobs\research-job.json `
  evidence\research-job-import-report.json
```

Exit code `0` means every row was translated. Exit code `2` means at least one
row needs manual review. Valid rows are still written to the job when other
rows need review. Exit code `1` means the document or output operation failed.

The importer never overwrites an existing job or report.

## Guided import and collection

Run:

```powershell
python -m blockchain_collector.menu
```

Choose **Import structured verification requests**. The menu writes:

- `jobs/<name>.json`
- `evidence/<name>-import-report.json`
- `evidence/<name>.json`
- `evidence/<name>.md`

When no rows are supported, only the import report is written. When some rows
need manual review, the supported rows still run and the menu returns the
partial-result exit code.
