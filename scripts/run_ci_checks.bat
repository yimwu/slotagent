@echo off
REM Local CI validation script for Windows
REM Runs all checks that GitHub Actions CI performs

setlocal enabledelayedexpansion
set FAILED_CHECKS=0

echo ======================================
echo Starting Local CI Validation
echo ======================================
echo.

REM 1. Black formatting check
echo --------------------------------------
echo Running: Black code formatting
echo --------------------------------------
black --check src/slotagent tests/
if %errorlevel% neq 0 (
    echo [FAILED] Black code formatting
    set /a FAILED_CHECKS+=1
) else (
    echo [PASSED] Black code formatting
)
echo.

REM 2. isort import sorting check
echo --------------------------------------
echo Running: isort import sorting
echo --------------------------------------
isort --check-only src/slotagent tests/
if %errorlevel% neq 0 (
    echo [FAILED] isort import sorting
    set /a FAILED_CHECKS+=1
) else (
    echo [PASSED] isort import sorting
)
echo.

REM 3. Flake8 lint check
echo --------------------------------------
echo Running: Flake8 linting
echo --------------------------------------
flake8 src/slotagent tests/ --max-line-length=100 --extend-ignore=E203,E501
if %errorlevel% neq 0 (
    echo [FAILED] Flake8 linting
    set /a FAILED_CHECKS+=1
) else (
    echo [PASSED] Flake8 linting
)
echo.

REM 4. MyPy type checking (optional)
echo --------------------------------------
echo Running: MyPy type checking (optional)
echo --------------------------------------
mypy src/slotagent --ignore-missing-imports 2>nul
if %errorlevel% neq 0 (
    echo [SKIPPED] MyPy type checking (optional, not enforced in CI)
) else (
    echo [PASSED] MyPy type checking
)
echo.

REM 5. Run tests with coverage
echo --------------------------------------
echo Running: pytest tests
echo --------------------------------------
D:\software\Python312\python.exe -m pytest --cov=src/slotagent --cov-report=term-missing --cov-report=xml tests/
if %errorlevel% neq 0 (
    echo [FAILED] pytest tests
    set /a FAILED_CHECKS+=1
) else (
    echo [PASSED] pytest tests
)
echo.

REM 6. Check coverage threshold
echo --------------------------------------
echo Running: Coverage threshold check (85%%)
echo --------------------------------------
coverage report --fail-under=85
if %errorlevel% neq 0 (
    echo [FAILED] Coverage threshold (85%%)
    set /a FAILED_CHECKS+=1
) else (
    echo [PASSED] Coverage threshold (85%%)
)
echo.

REM 7. Radon complexity check (optional)
echo --------------------------------------
echo Running: Radon complexity check (optional)
echo --------------------------------------
radon cc src/slotagent -a -nb 2>nul
if %errorlevel% neq 0 (
    echo [SKIPPED] Radon not installed (optional check)
) else (
    radon mi src/slotagent -nb
    echo [INFO] Radon complexity check (informational only)
)
echo.

REM Summary
echo ======================================
echo CI Validation Summary
echo ======================================

if %FAILED_CHECKS% equ 0 (
    echo [SUCCESS] ALL CHECKS PASSED!
    echo.
    echo Your code is ready to pass GitHub CI.
    exit /b 0
) else (
    echo [FAILURE] %FAILED_CHECKS% CHECK(S) FAILED
    echo.
    echo Please fix the issues above before pushing.
    exit /b 1
)
