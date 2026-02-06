# Security Review Command

Perform a focused security audit on the codebase.

## Git Repository
This project's git repository is located at `fnf-marketing-dashboard/` directory.
**All git commands must be executed with `-C fnf-marketing-dashboard` option.**

## Target
$ARGUMENTS

If no target specified, scan the entire codebase for security vulnerabilities.

## Security Audit Checklist

### 1. Authentication & Authorization
- [ ] Azure AD / MSAL configuration security
- [ ] JWT token handling and validation
- [ ] Session management
- [ ] Protected routes enforcement
- [ ] Role-based access control (if applicable)

### 2. Injection Vulnerabilities
- [ ] SQL Injection in Snowflake queries
  - Parameterized queries usage
  - Dynamic query construction
- [ ] Command Injection
- [ ] NoSQL Injection
- [ ] LDAP Injection

### 3. XSS (Cross-Site Scripting)
- [ ] User input rendering in React
- [ ] dangerouslySetInnerHTML usage
- [ ] URL parameter handling
- [ ] DOM manipulation

### 4. Sensitive Data Exposure
- [ ] .env files and secrets in code
- [ ] API keys hardcoded
- [ ] Credentials in logs
- [ ] Error messages leaking info
- [ ] .gitignore coverage

### 5. API Security
- [ ] CORS configuration
- [ ] Rate limiting
- [ ] Input validation (DTOs)
- [ ] Response data filtering
- [ ] HTTP security headers

### 6. Dependency Security
- [ ] Known vulnerable packages
- [ ] Outdated dependencies
- [ ] Supply chain risks

## Critical Files to Review

```
# Server
fnf-marketing-dashboard/server/src/auth/           # Authentication logic
fnf-marketing-dashboard/server/src/**/*.service.ts # Business logic with DB
fnf-marketing-dashboard/server/.env*               # Environment config

# Client
fnf-marketing-dashboard/client/lib/auth/           # Client auth handling
fnf-marketing-dashboard/client/app/api/            # API routes
```

## Instructions

1. Search for security-sensitive patterns:
   - Direct SQL string concatenation
   - eval(), Function() usage
   - innerHTML/dangerouslySetInnerHTML
   - process.env exposure to client
   - Hardcoded credentials

2. Review authentication flow end-to-end

3. Check all API endpoints for proper authorization

4. Verify input validation on all user inputs

## Output Format

```
## Security Audit Report

### Risk Summary
- Critical: X | High: X | Medium: X | Low: X

### Critical Vulnerabilities
[Immediate action required]

### High Risk Issues
[Should be fixed before production]

### Medium Risk Issues
[Should be addressed soon]

### Low Risk / Informational
[Best practice recommendations]

### Security Recommendations
[General security improvements]
```

## Begin Security Audit

Thoroughly scan the codebase for security vulnerabilities.
