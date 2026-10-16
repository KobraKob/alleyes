# ALLEYES Dashboard

The dashboard reads business-scoped records from the ALLEYES FastAPI backend. It does not ship example leads, campaign metrics, learning curves, or audit rows.

## Run locally

From this directory:

```bash
npm ci
npm run dev
```

Open `http://localhost:3000`. Select **Connect workspace** and enter:

- API base URL (the FastAPI origin, without an endpoint path)
- Business ID (UUID belonging to the API key)
- API key issued for that business
- Reviewer user ID (optional for read-only use; required by approval/rejection endpoints)

Set `NEXT_PUBLIC_ALLEYES_API_URL` to prefill the API URL in the connection form. This variable is an origin, not a secret.

## Backend requirements

- The dashboard origin must be listed in the backend's `CORS_ORIGINS`.
- The API key must belong to the selected business. The API enforces this pairing.
- Workspace credentials are kept in browser `sessionStorage` and are cleared when the browser session ends. They are still accessible to JavaScript running in the page; use a server-side session/proxy architecture before deploying a multi-user public dashboard.
- Approval endpoints call the backend executor. Approving an action may have external side effects depending on the server's configured safety mode.
- The backend currently exposes no GET endpoint for kill-switch state, autonomy policy configuration, audit history, or arm posterior statistics. The dashboard marks those capabilities unavailable rather than substituting examples.

## Live data sources

| View | API source |
| --- | --- |
| Overview | `/v1/reports/weekly`, `/v1/reports/campaigns`, `/v1/objectives`, `/v1/locations`, `/v1/insights` |
| Action desk | `/v1/actions`, `/v1/actions/{id}/approve`, `/v1/actions/{id}/reject` |
| Performance | Funnel report, campaign report, objectives and locations |
| Learning lab | `/v1/insights`, `/v1/packs` |
| System control | `/health`, `/ready`, `/v1/kill-switch` |

Operational data refreshes on a 30-second interval while a workspace is connected. Pages also provide a manual refresh action. Errors are surfaced, and failed endpoints do not retain stale metrics as if they were current.
