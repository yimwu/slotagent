#!/bin/bash
# Local CI validation script
# Runs all checks that GitHub Actions CI performs

set -e  # Exit on first error

echo "======================================"
echo "Starting Local CI Validation"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
FAILED_CHECKS=()

# Function to run a check
run_check() {
    local check_name="$1"
    shift
    echo "--------------------------------------"
    echo "Running: $check_name"
    echo "--------------------------------------"
    if "$@"; then
        echo -e "${GREEN}✓ PASSED${NC}: $check_name"
        echo ""
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}: $check_name"
        echo ""
        FAILED_CHECKS+=("$check_name")
        return 1
    fi
}

# 1. Black formatting check
run_check "Black code formatting" black --check src/slotagent tests/ || true

# 2. isort import sorting check
run_check "isort import sorting" isort --check-only src/slotagent tests/ || true

# 3. Flake8 lint check
run_check "Flake8 linting" flake8 src/slotagent tests/ --max-line-length=100 --extend-ignore=E203,E501 || true

# 4. MyPy type checking (optional in CI)
echo "--------------------------------------"
echo "Running: MyPy type checking (optional)"
echo "--------------------------------------"
if mypy src/slotagent --ignore-missing-imports 2>/dev/null; then
    echo -e "${GREEN}✓ PASSED${NC}: MyPy type checking"
else
    echo -e "${YELLOW}⚠ SKIPPED${NC}: MyPy type checking (optional, not enforced in CI)"
fi
echo ""

# 5. Run tests with coverage
run_check "pytest tests" pytest --cov=src/slotagent --cov-report=term-missing --cov-report=xml tests/ || true

# 6. Check coverage threshold
run_check "Coverage threshold (85%)" coverage report --fail-under=85 || true

# 7. Radon complexity check (optional in CI)
echo "--------------------------------------"
echo "Running: Radon complexity check (optional)"
echo "--------------------------------------"
if command -v radon &> /dev/null; then
    radon cc src/slotagent -a -nb
    radon mi src/slotagent -nb
    echo -e "${YELLOW}ℹ INFO${NC}: Radon complexity check (informational only)"
else
    echo -e "${YELLOW}⚠ SKIPPED${NC}: Radon not installed (optional check)"
fi
echo ""

# Summary
echo "======================================"
echo "CI Validation Summary"
echo "======================================"

if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED!${NC}"
    echo ""
    echo "Your code is ready to pass GitHub CI."
    exit 0
else
    echo -e "${RED}✗ ${#FAILED_CHECKS[@]} CHECK(S) FAILED:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo -e "  ${RED}-${NC} $check"
    done
    echo ""
    echo "Please fix the issues above before pushing."
    exit 1
fi
