# Odoo

[![Build Status](https://runbot.odoo.com/runbot/badge/flat/1/master.svg)](https://runbot.odoo.com/runbot)
[![Tech Doc](https://img.shields.io/badge/master-docs-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/documentation/master)
[![Help](https://img.shields.io/badge/master-help-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/forum/help-1)
[![Nightly Builds](https://img.shields.io/badge/master-nightly-875A7B.svg?style=flat&colorA=8F8F8F)](https://nightly.odoo.com/)

Odoo is a suite of web based open source business apps.

The main Odoo Apps include an [Open Source CRM](https://www.odoo.com/page/crm),
[Website Builder](https://www.odoo.com/app/website),
[eCommerce](https://www.odoo.com/app/ecommerce),
[Warehouse Management](https://www.odoo.com/app/inventory),
[Project Management](https://www.odoo.com/app/project),
[Billing &amp; Accounting](https://www.odoo.com/app/accounting),
[Point of Sale](https://www.odoo.com/app/point-of-sale-shop),
[Human Resources](https://www.odoo.com/app/employees),
[Marketing](https://www.odoo.com/app/social-marketing),
[Manufacturing](https://www.odoo.com/app/manufacturing),
[...](https://www.odoo.com/)

Odoo Apps can be used as stand-alone applications, but they also integrate seamlessly so you get
a full-featured [Open Source ERP](https://www.odoo.com) when you install several Apps.

## Getting started with Odoo

For a standard installation please follow the [Setup instructions](https://www.odoo.com/documentation/master/administration/install/install.html)
from the documentation.

To learn the software, we recommend the [Odoo eLearning](https://www.odoo.com/slides),
or [Scale-up, the business game](https://www.odoo.com/page/scale-up-business-game).
Developers can start with [the developer tutorials](https://www.odoo.com/documentation/master/developer/howtos.html).

## Development container

This repository includes a VS Code devcontainer in `.devcontainer/`.

1. Open the repo in VS Code and choose **Reopen in Container**.
2. Update `.devcontainer/odoo.conf` with your external PostgreSQL settings.
3. Run Odoo from the workspace:

```bash
./odoo-bin -c .devcontainer/odoo.conf
```

The devcontainer does not run PostgreSQL. Use an external database endpoint.

## Container image

This repository includes a production-oriented `Dockerfile` for the Odoo service.
It expects PostgreSQL to be provided externally.

Build:

```bash
docker build -t odoo:local .
```

Run:

```bash
docker run --rm -p 8069:8069 -p 8072:8072 \
  -e ODOO_DB_HOST=<postgres-host> \
  -e ODOO_DB_PORT=5432 \
  -e ODOO_DB_USER=odoo \
  -e ODOO_DB_PASSWORD=<postgres-password> \
  -e ODOO_DB_NAME=False \
  odoo:local
```

## CI image builds

- GitHub Actions workflow: `.github/workflows/container-image.yml`
- GitLab pipeline: `.gitlab-ci.yml`

Both pipelines build the Odoo image. They are configured to push images to their
native registries (GHCR for GitHub and the project registry for GitLab).

## CI chart publishing

- GitHub Actions workflow: `.github/workflows/helm-chart.yml`
- GitLab pipeline job: `helm-chart-publish` in `.gitlab-ci.yml`

The chart in `charts/odoo` is published as an OCI Helm chart.
- GitHub publishes to: `oci://ghcr.io/<org>/charts/odoo`
- GitLab publishes to: `oci://<gitlab-registry>/<group>/<project>/charts/odoo`

Branch/default-branch pipelines publish `-dev.*` chart versions.
Tag pipelines publish the chart version from `charts/odoo/Chart.yaml`.

## Helm chart

A Helm chart is provided at `charts/odoo`.

This chart deploys only the Odoo service and requires external PostgreSQL values.
It supports route exposure via either Kubernetes Ingress or Gateway API.
It also supports optional DB bootstrap/migration hooks to avoid first-start crash loops.

Install from OCI (example using GHCR):

```bash
helm install odoo oci://ghcr.io/<org>/charts/odoo --version <chart-version>
```

Example:

```bash
helm upgrade --install odoo charts/odoo \
  --set image.repository=ghcr.io/<org>/<image> \
  --set image.tag=<tag> \
  --set odoo.config.dbHost=<postgres-host> \
  --set odoo.config.dbUser=odoo \
  --set odoo.config.dbPassword=<postgres-password> \
  --set exposure.enabled=true \
  --set exposure.type=gateway \
  --set gateway.route.parentRefs[0].name=<gateway-name>
```

To use cert-manager certificates:

```bash
--set certificate.enabled=true \
--set certificate.issuerRef.name=<issuer-name> \
--set certificate.annotations.\"example\\.com/team\"=<value>
```

Optional automatic DB bootstrap/migrations:

```yaml
databaseMaintenance:
  enabled: true
  serviceAccountName: default
  initOnInstall: true
  initModules: base
  migrateOnUpgrade: true
  migrationModules: all
```

When enabled, the chart runs:
- A pre-install hook Job that initializes the configured DB if it does not exist or is uninitialized (for example, an empty pre-created DB).
- A pre-upgrade hook Job that runs module upgrades (`-u`) on the configured DB.

`odoo.config.dbName` must be set to a concrete database name (not `False`) when using this feature.

## Security

If you believe you have found a security issue, check our [Responsible Disclosure page](https://www.odoo.com/security-report)
for details and get in touch with us via email.
