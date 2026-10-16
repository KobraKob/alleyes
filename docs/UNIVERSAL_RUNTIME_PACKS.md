# Universal ALLEYES Runtime Packs

ALLEYES is not a gym-only product. Vertical packs are runtime configuration for
business workflows; the engine remains shared across industries.

## Runtime contract

- Put each vertical in `packs/<slug>/pack.yaml`.
- The file must declare matching `slug`, `name`, and `version`.
- Optional `funnel_stages`, `decision_points`, and `channels` must be lists.
- Stage and decision-point entries must have unique string `key` values.
- Packs are parsed with `yaml.safe_load`; pack files are data, never executable code.
- `GET /v1/packs` lists discovered packs; `GET /v1/packs/{slug}` returns a validated pack.
- The registry reads from disk per request. A new pack is discoverable without an app rebuild.
- Set `ALLEYES_PACKS_DIR` to point at a mounted pack directory in deployments.

## Scope and integration boundary

This patch makes pack discovery dynamic; it does not pretend that adding a YAML file
automatically provisions database rows, ads accounts, consent, messaging templates, or
provider credentials. Those require explicit provisioning and connector-specific OAuth/webhook
setup. External actions must continue through the existing policy/approval/executor pipeline.

## Suggested starter verticals

Use the same shared engine for gyms, real estate, ecommerce, clinics, education, restaurants,
home services, professional services, SaaS, and local retail. Each pack should define its own
funnel stages, decision points, channels, reward weights, and compliance rules. Avoid embedding
industry assumptions in agent prompts or database logic; pass the active pack as validated
tenant context.
