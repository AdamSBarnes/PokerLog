# Deployment
Deployment is configured. See below for the chosen stack and setup instructions.

## Stack
| Component | Service | Tier | Estimated Cost |
|-----------|---------|------|----------------|
| Backend | [Fly.io](https://fly.io) | Free (shared-cpu-1x, 256 MB) | $0/mo |
| Database | SQLite on Fly.io persistent volume | 1 GB included | $0/mo |
| DB backup | Local (`fly ssh sftp get`) | — | $0/mo |
| Frontend | [Netlify](https://netlify.com) | Free (100 GB bandwidth) | $0/mo |
| CI/CD | GitHub Actions | Free (2 000 min/mo private) | $0/mo |

## Setup instructions
See the **Deployment** section in `README.md`.
