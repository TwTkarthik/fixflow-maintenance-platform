# FixFlow container and deployment guide

Phase 11 adds a reproducible local Docker Compose workflow. It packages the existing FastAPI, React/Vite, and PostgreSQL services without changing the application architecture or database contract.

## Local Docker Compose

Prerequisites:

- Docker Desktop with the Linux engine running.
- A local `.env` copied from the root `.env.example`.
- A random `JWT_SECRET_KEY` of at least 32 characters.

From the repository root:

```powershell
Copy-Item .env.example .env
# Edit .env and replace POSTGRES_PASSWORD and JWT_SECRET_KEY.
docker compose --env-file .env config
docker compose --env-file .env up --build
```

The services are then available at:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/api/health`
- Backend API documentation: `http://localhost:8000/docs`

The `migrate` service runs `alembic upgrade head` after PostgreSQL is healthy and before the API starts. It is a one-shot service; migration output should be reviewed before treating a deployment as ready.

The backend and frontend images each include a health check. Compose waits for the database, migration service, and backend health before starting the frontend. The PostgreSQL data is stored in the named `fixflow_postgres_data` volume so normal container restarts do not discard application data.

To stop the stack while retaining the database volume:

```powershell
docker compose --env-file .env down
```

Do not use `docker compose down -v` unless intentionally deleting the local database volume. The Compose credentials and JWT secret are local configuration only; never commit `.env` or use these development defaults for production.

## Configuration and production handling

The Compose file passes `DATABASE_URL`, PostgreSQL's `PGPASSWORD`, `FIXFLOW_CORS_ORIGINS`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, and `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` to the backend through environment variables. Keeping the database password out of `DATABASE_URL` avoids breaking passwords containing URL-reserved characters. `VITE_API_BASE_URL` is a build-time frontend value because Vite embeds it into the static bundle. Production deployments must provide a browser-reachable HTTPS API URL and a narrowly scoped HTTPS CORS origin.

The PostgreSQL volume is suitable for local persistence, not a production backup strategy. A production deployment needs managed encrypted storage, backups, restore testing, restricted network access, rotated credentials, TLS, log/metric collection, and a deliberate migration-release process. Do not expose PostgreSQL publicly.

## Optional AWS architecture

AWS deployment is optional and was not performed in Phase 11. A proportionate future architecture would be:

1. Build and scan the backend and frontend images in CI.
2. Push versioned images to Amazon ECR.
3. Run the backend and frontend as separate ECS Fargate services behind an Application Load Balancer.
4. Use Amazon RDS for PostgreSQL in private subnets, with automated backups and security groups allowing database traffic only from the backend service.
5. Store `JWT_SECRET_KEY`, database credentials, and other sensitive configuration in AWS Secrets Manager or SSM Parameter Store, not in images or task definitions.
6. Run the reviewed Alembic migration as a release job before switching traffic to the new backend revision.
7. Terminate TLS at the load balancer, restrict CORS to the deployed frontend origin, and expose only the frontend/API listener publicly.
8. Add CloudWatch logs, health-check alarms, least-privilege IAM roles, and a documented rollback plan.

This is an architecture note, not a deployment claim. No AWS resources, credentials, infrastructure-as-code, or production secrets are included in the repository.

## Verification boundary

Phase 11 can validate Compose configuration statically with `docker compose config`. A real image build and container smoke run require a working Docker daemon. The current development environment has Docker CLI and Compose installed, but Docker Desktop's Linux engine is not running, so no container build or runtime result is claimed until that prerequisite is available.
