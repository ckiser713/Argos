cd backend && ../tools/ensure_python311_poetry.sh && poetry install --no-root
cd .. && pnpm install
pnpm exec playwright install
cd ops && docker-compose up -d qdrant
cd .. && pnpm e2e