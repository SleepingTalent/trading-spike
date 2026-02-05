# Project Instructions

> Adapted from [github/awesome-copilot](https://github.com/github/awesome-copilot) instructions

---

## Code Review Standards

### Priority Levels
- **CRITICAL** (blocks merge): Security vulnerabilities, correctness issues, breaking changes, data loss risks
- **IMPORTANT** (requires discussion): Code quality, test coverage, performance, architecture
- **SUGGESTION** (non-blocking): Readability, optimization, conventions, documentation

### Core Principles
- Be specific with line references
- Explain WHY issues matter, not just what
- Suggest concrete solutions
- Acknowledge good code
- Group related feedback

### Code Quality
- Use meaningful, descriptive names
- Single responsibility for functions and classes
- Avoid duplication (DRY)
- Keep functions small and focused
- Limit nesting depth
- No magic numbers - use named constants
- Write self-documenting code

### Error Handling
- Handle exceptions at appropriate levels
- Use meaningful error messages
- Never fail silently
- Validate inputs early (fail fast)
- Use appropriate error types

---

## Security (OWASP Top 10)

### Access Control (A01, A10)
- Implement least privilege with explicit permission checks
- Follow "deny by default" pattern for all access decisions
- Validate user-provided URLs against allowlists
- Sanitize file paths to prevent directory traversal

### Cryptography (A02)
- Use Argon2 or bcrypt for passwords; never MD5/SHA-1
- Always use HTTPS for network requests
- Encrypt sensitive data at rest with AES-256
- Load secrets from environment variables or vault services - never hardcode

### Injection Prevention (A03)
- Use parameterized queries exclusively - no string concatenation for SQL
- Escape command-line arguments properly
- Prevent XSS using text-safe methods; sanitize HTML with DOMPurify when needed

### Configuration & Dependencies (A05, A06)
- Disable debug features and verbose errors in production
- Add security headers: CSP, HSTS, X-Content-Type-Options
- Use latest stable dependency versions
- Run vulnerability scanners regularly

### Authentication (A07)
- Generate new session IDs post-login
- Set cookie attributes: HttpOnly, Secure, SameSite=Strict
- Implement rate limiting and account lockout

### Data Integrity (A08)
- Avoid deserializing untrusted data
- Prefer JSON over unsafe formats with strict type checking

---

## TypeScript Guidelines

### Core Standards
- Use pure ES modules (no CommonJS)
- PascalCase for classes/interfaces; camelCase elsewhere
- Avoid `any` types; prefer `unknown` with type narrowing
- Use `async/await` wrapped in try/catch blocks

### Architecture
- Follow existing folder structures and responsibility layouts
- Use kebab-case filenames (e.g., `user-session.ts`)
- Keep tests near implementations
- Maintain decoupled layers: transport, domain, presentation

### Best Practices
- Validate external input with schema validators (Zod, etc.)
- Sanitize content before rendering HTML
- Apply parameterized queries
- Lazy-load heavy dependencies
- Track resource lifetimes to prevent leaks
- Include JSDoc for public APIs

---

## Python Guidelines

### Style
- Follow PEP 8 strictly
- 4-space indentation, 79-character line limit
- Use type hints from the `typing` module
- Follow PEP 257 docstring conventions

### Documentation
```python
def calculate_area(radius: float) -> float:
    """Calculate the area of a circle given the radius.

    Parameters:
        radius (float): The radius of the circle.

    Returns:
        float: The area of the circle, calculated as π * radius².
    """
```

### Testing
- Write unit tests for critical functionality
- Handle edge cases: empty inputs, invalid types, large datasets
- Document expected behaviors

---

## DevOps Principles (CALMS)

### Culture
- Foster collaboration and shared responsibility
- Practice blameless post-mortems
- People and interactions are paramount

### Automation
- Automate CI/CD pipelines
- Use infrastructure-as-code
- Automate testing and security scanning
- If it's repeatable, automate it

### Lean
- Eliminate waste, maximize flow
- Deliver in smaller batches
- Practice just-in-time delivery

### Measurement (DORA Metrics)
- Deployment Frequency (elite: multiple daily)
- Lead Time for Changes (elite: <1 hour)
- Change Failure Rate (elite: 0-15%)
- Mean Time to Recovery (elite: <1 hour)

### Sharing
- Document knowledge
- Use communication channels effectively
- Encourage cross-functional collaboration

---

## Testing Standards

- Adequate coverage for critical paths
- Descriptive test names
- Clear structure: Arrange-Act-Assert
- Tests must be independent
- Use specific assertions
- Cover edge cases
- Mock appropriately

---

## GitHub Actions CI/CD

### Workflow Organization
- Use descriptive naming conventions
- Choose appropriate triggers: `push`, `pull_request`, `workflow_dispatch`, `schedule`
- Set concurrency controls to prevent resource conflicts
- Apply explicit permissions at workflow and job levels (least-privilege)

### Job Architecture
- Jobs represent distinct pipeline phases (build, test, deploy)
- Use `needs` for dependency management
- Use `outputs` for inter-job communication
- Use `if` conditions for conditional execution

### Security
- **Secrets**: Use `secrets.<NAME>` context exclusively for sensitive data
- **Tokens**: Default `GITHUB_TOKEN` to read-only; grant write only when essential
- **OIDC**: Prefer OpenID Connect for cloud provider auth (no long-lived credentials)
- **Scanning**: Integrate SCA, SAST, and secret scanning

### Performance
- **Caching**: Use `actions/cache` with `hashFiles('**/package-lock.json')` key strategies
- **Parallelization**: Use matrix strategies for concurrent testing across configurations
- **Checkout**: Use `fetch-depth: 1` for shallow clones
- **Artifacts**: Use `actions/upload-artifact` / `actions/download-artifact` for inter-job data

### Actions Best Practices
- Pin actions to specific versions or commit SHAs (not floating tags)
- Use descriptive step names for clear logging
- Combine shell commands efficiently

### Deployment Patterns
- **Environment progression**: Staging → Production with manual approvals
- **Strategies**: Rolling updates, blue/green, canary releases, feature flags
- **Resilience**: Version artifacts for quick recovery; automate rollback on alerts

---

## Docker & Containerization

### Core Principles
- **Immutability**: Images unchanged after build; version and tag meaningfully
- **Portability**: Run consistently across environments without modification
- **Isolation**: Single process per container; use container networking
- **Efficiency**: Prioritize small images (faster builds, smaller attack surface)

### Dockerfile Best Practices
- **Multi-stage builds**: Separate build-time and runtime dependencies
- **Base images**: Use official minimal variants (alpine, slim, distroless) with specific version tags - never `latest` in production
- **Layer optimization**: Order from least to most frequently changing; combine RUN commands
- **`.dockerignore`**: Exclude .git, node_modules, build artifacts, dev files
- **Selective COPY**: Copy dependency files before source code for better caching

### Security
- **Non-root users**: Always create and use dedicated non-root users
- **Minimal base images**: Fewer packages = fewer vulnerabilities
- **Scanning**: Integrate hadolint (Dockerfile linting) and Trivy/Snyk (vulnerability scanning)
- **No secrets in layers**: Never include passwords, keys, or credentials
- **Capability restrictions**: Drop unnecessary Linux capabilities

### Configuration
- Use exec form for CMD/ENTRYPOINT (better signal handling):
  ```dockerfile
  ENTRYPOINT ["node", "server.js"]
  CMD ["--port", "3000"]
  ```
- Externalize config through environment variables with sensible defaults
- Include HEALTHCHECK instructions for orchestration

### Runtime
- **Resource limits**: Set CPU and memory limits
- **Logging**: Use structured logging (JSON), centralize logs
- **Storage**: Use named volumes for persistence, never container layers
- **Networking**: Create custom networks for isolation
