# GitHub Actions CI/CD

This directory contains GitHub Actions workflows for automated testing and deployment.

## Workflows

### Check Workflows (Run on Pull Requests)

#### `check_python.yml`
- **Trigger**: Pull requests
- **Jobs**:
  - `test-python`: Run pytest tests
  - `lint-python`: Run ruff linting and format checks
- **Working directory**: `./python/x402`

#### `check_typescript.yml`
- **Trigger**: Pull requests
- **Jobs**:
  - `lint-typescript`: Run ESLint
  - `build-typescript`: Build all packages
  - `test-typescript`: Run tests on Node.js 18, 20, 22
- **Working directory**: `./typescript`

#### `e2e_tests.yml`
- **Trigger**: Pull requests, manual dispatch
- **Jobs**:
  - `e2e-tests`: Run end-to-end integration tests
- **Working directory**: `./e2e`

### Publish Workflows (Manual Trigger)

#### `publish_npm.yml`
- **Trigger**: Manual (`workflow_dispatch`)
- **Input**: NPM tag (latest, beta, alpha)
- **Package**: `@sun-protocol/tvm-x402`
- **Protection**: Only publishes on `main` branch (dry-run on other branches)
- **Authentication**: Uses OIDC trusted publishing (no token needed)

#### `publish_pypi.yml`
- **Trigger**: Manual (`workflow_dispatch`)
- **Package**: `tvm-x402`
- **Protection**: Only publishes on `main` branch
- **Authentication**: Uses OIDC trusted publishing (no token needed)

## Setup Requirements

### For NPM Publishing

1. **Configure NPM Trusted Publishing**:
   - Go to https://www.npmjs.com/settings/sun-protocol/packages/@sun-protocol/tvm-x402/access
   - Enable "Automation tokens"
   - Add GitHub Actions as trusted publisher:
     - Repository: `sun-protocol/tvm-x402`
     - Workflow: `publish_npm.yml`
     - Environment: `npm`

2. **Create GitHub Environment**:
   - Go to repository Settings → Environments
   - Create environment named `npm`
   - Add protection rules (require reviewers, restrict to `main` branch)

### For PyPI Publishing

1. **Configure PyPI Trusted Publishing**:
   - Go to https://pypi.org/manage/account/publishing/
   - Add a new publisher:
     - Repository: `sun-protocol/tvm-x402`
     - Workflow: `publish_pypi.yml`
     - Environment: `pypi`

2. **Create GitHub Environment**:
   - Go to repository Settings → Environments
   - Create environment named `pypi`
   - Add protection rules (require reviewers, restrict to `main` branch)

## Usage

### Running Checks Locally

**Python**:
```bash
cd python/x402
uvx ruff check
uvx ruff format --check
uv run pytest
```

**TypeScript**:
```bash
cd typescript
pnpm lint
pnpm build
pnpm test
```

**E2E**:
```bash
cd e2e
uv run pytest -v
```

### Publishing Packages

1. **Bump version** in the appropriate `package.json` or `pyproject.toml`
2. **Commit and push** to `main` branch
3. **Go to Actions tab** in GitHub
4. **Select the publish workflow** (npm or pypi)
5. **Click "Run workflow"**
6. **Select branch** (must be `main` for actual publish)
7. **For NPM**: Choose tag (latest/beta/alpha)
8. **Click "Run workflow"**

### Monitoring

- Check workflow runs in the **Actions** tab
- Failed checks will block PR merges
- Publish workflows require manual approval if environment protection is enabled

## Troubleshooting

### NPM Publish Fails

- Verify version is bumped (npm won't publish duplicate versions)
- Check NPM trusted publishing is configured correctly
- Ensure workflow is running on `main` branch
- Verify package builds successfully: `cd typescript && pnpm build`

### PyPI Publish Fails

- Verify version is bumped in `pyproject.toml`
- Check PyPI trusted publishing is configured correctly
- Ensure workflow is running on `main` branch
- Verify package builds: `cd python/x402 && uv build`

### Tests Fail

- Run tests locally first to debug
- Check if dependencies are up to date
- Review test logs in Actions tab
- Ensure all required environment variables are set
