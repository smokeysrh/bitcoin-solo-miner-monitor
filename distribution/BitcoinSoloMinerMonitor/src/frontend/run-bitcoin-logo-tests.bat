@echo off
echo Running BitcoinLogo Component Tests...
echo.
npx vitest run tests/unit/components/BitcoinLogo.test.js
echo.
echo Test run complete!
pause