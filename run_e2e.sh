cd backend && poetry env use /nix/store/00x3abm7y8j13i6n4sahvbar99irkc7d-python3-3.11.14/bin/python3 && poetry install --no-root
cd .. && pnpm install
pnpm exec playwright install
cd ops && docker-compose up -d qdrant
cd .. && pnpm e2e