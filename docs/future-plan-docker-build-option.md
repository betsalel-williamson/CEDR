# Future plan: Choose pre-built image vs local Dockerfile

**Status:** Draft — confirm with maintainer before implementing.

## Goal

Support two ways to run the CEDR tutorial environment:

1. **Pre-built image** (current): use `uofarcl/cedr:tutorial_isfpga26` from the registry.
2. **Local build**: build and run from the repo's [Dockerfile](Dockerfile) instead.

User can choose per run (e.g. via Make target or Compose override) without editing the main compose file by default.

---

## Option A: Pre-built image (`uofarcl/cedr:tutorial_isfpga26`)

| Pros | Cons |
|------|------|
| No build step; `make up` is fast | Image may be older than your repo |
| Same environment as course/tutorial | No way to change base or deps without forking image |
| No local disk for build cache | Requires `platform: linux/amd64` on Mac M2 (arm64) |
| Works offline after first pull | Tag/tag updates controlled by image publisher |

**Best for:** Following the tutorial as-is, quick iteration, or when you don't need to change the image.

---

## Option B: Local Dockerfile (build from [Dockerfile](Dockerfile))

| Pros | Cons |
|------|------|
| Image matches current repo (deps, scripts) | First build is slow (apt, install_dependencies.sh) |
| You can change Dockerfile and rebuild | Build cache and disk usage on your machine |
| Same platform as host if you build on M2 (arm64) | Slightly more setup (build step, possibly two "modes") |
| Good for development and customizations | Repo Dockerfile may differ from pre-built (e.g. Ubuntu 18.04 vs image's base) |

**Best for:** Development, custom dependencies, or when the pre-built image is out of date or wrong for your branch.

---

## Possible implementation approaches

1. **Makefile targets**  
   - `make up` → keep using pre-built image (current).  
   - `make up-local` (or `make build-up`) → build from Dockerfile, then `up` with the built image.  
   - Compose could stay single-file; Make passes a different compose file or override that uses `build: .` instead of `image:`.

2. **Compose override**  
   - `docker-compose.override.yml` (e.g. `build: .`, no `image:`), used when present so `docker-compose up` builds and runs locally.  
   - Default (no override) = pre-built image.  
   - Document: "To use local Dockerfile, add an override that sets `build: .` for the service."

3. **Env-based choice**  
   - e.g. `USE_LOCAL_BUILD=1 make up` → use a compose file or override that uses `build: .`.  
   - Requires one extra compose file or an override template.

4. **Two compose files**  
   - `docker-compose.yml` = pre-built image (current).  
   - `docker-compose.local.yml` = build from Dockerfile; run with `docker-compose -f docker-compose.local.yml up -d`.  
   - Makefile targets wrap the right `-f` flag.

Recommendation: **Makefile targets** (e.g. `make up` vs `make up-local`) plus one extra compose file or override for the "local build" case keeps the default simple and documents the choice in `make help`.

---

## Open decisions (confirm before implementing)

- Default behavior: keep `make up` = pre-built image only?
- Naming: prefer `make up-local`, `make build-up`, or something else for "build from Dockerfile then up"?
- Should the local build use the same service/container name so `make shell` works for both?
- Any need to support both a "tutorial" image and a "dev" image (e.g. different tag vs local build) in the same compose project?

---

## Next step

**Please confirm:**

1. That you want this "pre-built vs local Dockerfile" option implemented.
2. Your preferred approach (Makefile targets, override, two compose files, or other).
3. Names for targets (e.g. `up` vs `up-local` / `build-up`).

After you confirm, this can be turned into a concrete implementation plan (steps and file changes) and then implemented.
