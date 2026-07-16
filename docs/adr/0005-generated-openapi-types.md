# ADR 0005: Generated OpenAPI types

- Status: accepted
- Decision: FastAPI OpenAPI is exported and converted to committed TypeScript definitions; browser access uses one typed client.
- Rationale: this prevents independent backend/frontend API models from drifting.
- Consequence: contract generation and a clean generated diff are required CI gates.
