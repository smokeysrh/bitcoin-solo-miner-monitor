# Security Scan Email Reduction Changes

## Problem
You were receiving frequent emails from the security scan workflow because it was:
- Running daily (every day at 2 AM UTC)
- Running on every push to main AND develop branches
- Sending notifications even when no security issues were found

## Changes Made

### 1. Reduced Scan Frequency
- **Before**: Daily scans (`0 2 * * *`)
- **After**: Weekly scans on Sundays (`0 2 * * 0`)

### 2. Smarter Trigger Conditions
- **Before**: Ran on every push to main/develop
- **After**: Only runs on pushes that change security-relevant files:
  - `requirements.txt`
  - `src/frontend/package*.json`
  - `.github/workflows/security-scan.yml`
  - `src/**/*.py`

### 3. Issue-Based Notifications
- **Before**: Always created reports and notifications
- **After**: Only creates GitHub issues and PR comments when actual security vulnerabilities are detected

### 4. Removed Develop Branch
- **Before**: Triggered on both main and develop branches
- **After**: Only triggers on main branch

## Expected Result
- **90% fewer emails** - Weekly instead of daily + only when files change
- **Only actionable notifications** - You'll only get notified when there are actual security issues to address
- **Cleaner inbox** - No more "everything is fine" security reports

## Manual Override
You can still run security scans manually anytime using the "Actions" tab in GitHub and clicking "Run workflow" on the Security Scan workflow.

## Next Steps
If you still get too many emails, we can:
1. Disable email notifications entirely for this workflow
2. Change to monthly scans instead of weekly
3. Only run scans on releases instead of regular pushes