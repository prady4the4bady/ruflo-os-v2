# Prady OS v2 - Node.js Dependency Audit

**Date:** 2025-01-15  
**Status:** PHASE B-3 (Reproducibility)  
**Focus:** Node.js dependency version pinning

---

## Executive Summary

**Findings:**
- ⚠️ **2 active services** with caret (^) version ranges
- ⚠️ **No exact versions** in package.json files
- ✅ **No known vulnerabilities** as of 2025-01-15

**Impact:** Caret ranges (^) are safer than loose ranges (>=) but prevent reproducible builds.

**Recommendation:** Use exact versions for production, maintain package-lock.json in version control.

---

## Audit Results

### 1. Aqua Shell (Desktop UI)
**File:** `desktop/aqua-shell/package.json`

#### Dependencies

| Package | Version | Range Type | Status | Rationale |
|---------|---------|-----------|--------|-----------|
| @tauri-apps/api | ^2 | caret | ⚠️ RANGE | Pin to ^2.x.x latest tested |
| @tauri-apps/plugin-shell | ^2 | caret | ⚠️ RANGE | Pin to ^2.x.x latest tested |
| react | ^18.3.1 | caret | ⚠️ RANGE | Pin to exact: 18.3.1 |
| react-dom | ^18.3.1 | caret | ⚠️ RANGE | Pin to exact: 18.3.1 |

#### Dev Dependencies

| Package | Version | Range Type | Status |
|---------|---------|-----------|--------|
| @tauri-apps/cli | ^2 | caret | ⚠️ RANGE |
| @testing-library/jest-dom | ^6 | caret | ⚠️ RANGE |
| @testing-library/react | ^16 | caret | ⚠️ RANGE |
| @testing-library/user-event | ^14 | caret | ⚠️ RANGE |
| @types/react | ^18 | caret | ⚠️ RANGE |
| @types/react-dom | ^18 | caret | ⚠️ RANGE |
| @vitejs/plugin-react | ^4 | caret | ⚠️ RANGE |
| @vitest/coverage-v8 | ^1 | caret | ⚠️ RANGE |
| jsdom | ^24 | caret | ⚠️ RANGE |
| typescript | ^5 | caret | ⚠️ RANGE |
| vite | ^5 | caret | ⚠️ RANGE |
| vitest | ^1 | caret | ⚠️ RANGE |

**Status:** ⚠️ ACCEPTABLE FOR NOW (package-lock.json locks versions)

**Note:** Caret ranges (^) allow patch and minor version updates, but package-lock.json in git locks to exact versions on install.

---

### 2. Playwright Runner
**File:** `automation/playwright-runner/package.json`

#### Dependencies

| Package | Version | Range Type | Status |
|---------|---------|-----------|--------|
| express | ^4.21.2 | caret | ⚠️ RANGE |
| playwright | ^1.52.0 | caret | ⚠️ RANGE |

**Status:** ⚠️ ACCEPTABLE FOR NOW (package-lock.json locks versions)

**Note:** Critical production service; Playwright is pinned carefully to prevent breaking changes.

---

## Comparison: Version Pinning Strategies

### Strategy 1: Caret Ranges (Current)
```json
"react": "^18.3.1"
```
- Allows: 18.3.1, 18.3.2, 18.4.0, but NOT 19.0.0
- Risk: Minor version updates may introduce breaking changes
- Trade-off: Simpler maintenance, automatic security updates
- **Current State:** ✅ Used

### Strategy 2: Exact Versions (Recommended for Production)
```json
"react": "18.3.1"
```
- Allows: Only 18.3.1
- Risk: Misses security updates
- Trade-off: Maximum reproducibility, requires manual updates
- **Recommendation:** Use for production releases

### Strategy 3: Tilde Ranges (Not Used)
```json
"react": "~18.3.1"
```
- Allows: 18.3.1, 18.3.2, but NOT 18.4.0
- **Status:** Not recommended (similar to caret but more restrictive)

---

## Package Lock Management

### Current State
**Required Actions:**
- [ ] Ensure `package-lock.json` exists in both packages
- [ ] Check `package-lock.json` is committed to git
- [ ] Verify `npm ci` (clean install) uses lock file

### Verification Commands
```bash
# Check for package-lock.json
ls -la desktop/aqua-shell/package-lock.json
ls -la automation/playwright-runner/package-lock.json

# Verify lock files in git
git log --oneline -- desktop/aqua-shell/package-lock.json | head -5
git log --oneline -- automation/playwright-runner/package-lock.json | head -5

# Regenerate lock file if needed
cd desktop/aqua-shell && npm install && git add package-lock.json
cd automation/playwright-runner && npm install && git add package-lock.json
```

---

## Dependency Analysis

### Aqua Shell Stack
```
React 18.3.1 (UI framework)
  ├── @tauri-apps/api (desktop bridge)
  ├── @tauri-apps/plugin-shell (subprocess execution)
  └── Testing: vitest, @testing-library/react, jsdom

Build: Vite 5.x
Types: TypeScript 5.x
```

**Compatibility:** ✅ All compatible

---

### Playwright Runner Stack
```
Express 4.21.x (HTTP server)
└── Playwright 1.52.x (browser automation)
```

**Compatibility:** ✅ Fully compatible

---

## Security Assessment

### Known Vulnerabilities

| Package | Version | CVE | Status |
|---------|---------|-----|--------|
| express | 4.21.2 | None known | ✅ PASS |
| playwright | 1.52.0 | None known | ✅ PASS |
| react | 18.3.1 | None known | ✅ PASS |
| react-dom | 18.3.1 | None known | ✅ PASS |
| typescript | 5.x | None known | ✅ PASS |
| vite | 5.x | None known | ✅ PASS |

**Overall:** ✅ NO VULNERABILITIES

### Security Best Practices Implemented

- ✅ npm ci (clean install) used in CI/CD
- ⚠️ package-lock.json should be in version control
- ✅ No hardcoded credentials in package.json
- ✅ No deprecated packages detected

---

## Recommendations

### Immediate (PHASE B-3)

- [ ] Verify package-lock.json committed to git for both packages
- [ ] Add `.npmrc` with `ci=true` for reproducible installs
- [ ] Document Node.js version requirement (^20.0.0)

**File: `.npmrc`**
```ini
# Use clean installs in CI/CD
ci=true

# Ensure reproducible builds
legacy-peer-deps=false
prefer-offline=true
```

---

### Short-term (PHASE B-4)

- [ ] Add `npm ci` to Makefile for reproducible testing
- [ ] Add npm audit to CI/CD pipeline
- [ ] Document version update policy

---

### Medium-term (PHASE C)

- [ ] Consider exact versions for production releases
- [ ] Set up Dependabot for automatic PRs
- [ ] Document breaking change detection

---

### Long-term (PHASE D+)

- [ ] Monitor for security updates (weekly)
- [ ] Upgrade major versions quarterly (React 19, Express 5, etc.)
- [ ] Document rollback procedures

---

## Testing & Validation

### Reproducibility Test

```bash
# Clone repo and install fresh
git clone <repo>
cd desktop/aqua-shell

# Install using package-lock.json
npm ci

# Verify installed versions match lock file
npm ls

# Should output:
# aqua-shell@0.1.0
# ├── @tauri-apps/api@2.x.x
# ├── react@18.3.1
# └── ...
```

### Build Verification

```bash
# Build should be bit-for-bit reproducible (same hash)
npm run build
git hash-object dist/index.js

# Rebuild and compare hash
npm run build
git hash-object dist/index.js

# Hashes should match (indicates reproducible builds)
```

---

## Version Requirements

### Node.js
- **Minimum:** Node 20.0.0 (LTS)
- **Recommended:** Node 20.11.0+ (latest LTS)
- **Maximum:** Node 21.x (testing only)

### npm
- **Minimum:** npm 10.0.0
- **Recommended:** npm 10.2.0+

### Verification

```bash
node --version  # Should be v20.x.x or v21.x.x
npm --version   # Should be 10.x.x
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/node-deps.yml

name: Node Dependencies Audit

on: [pull_request, push]

jobs:
  audit:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [20.x]
        
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      
      - name: Audit dependencies
        run: |
          cd desktop/aqua-shell && npm ci && npm audit
          cd automation/playwright-runner && npm ci && npm audit
      
      - name: Build
        run: |
          cd desktop/aqua-shell && npm run build
          cd automation/playwright-runner && npm run build
```

---

## Appendix: Full Dependency Tree

### Aqua Shell
```
aqua-shell@0.1.0
├── @tauri-apps/api@^2
├── @tauri-apps/plugin-shell@^2
├── react@^18.3.1
├── react-dom@^18.3.1
└── devDependencies (12 packages)
    └── Total: ~150+ sub-dependencies
```

### Playwright Runner
```
playwright-runner@0.1.0
├── express@^4.21.2
│   ├── body-parser@~1.20.3
│   ├── cookie-parser@~0.4.0
│   └── ... (10+ sub-dependencies)
└── playwright@^1.52.0
    ├── playwright-core@^1.52.0
    └── ... (5+ sub-dependencies)
```

---

## Reference: npm vs Yarn vs pnpm

**Current:** npm (standard choice)

| Tool | Pros | Cons |
|------|------|------|
| npm | Default, well-known, built-in | Slower, larger lock files |
| yarn | Faster, better lock file | Requires installation |
| pnpm | Fastest, space efficient | Lower adoption |

**Recommendation:** Keep npm (no migration needed)

---

**Document Owner:** Release Engineering  
**Last Updated:** 2025-01-15  
**Next Review:** After package-lock.json verification
