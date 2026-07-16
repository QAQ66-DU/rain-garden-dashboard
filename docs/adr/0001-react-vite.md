# ADR 0001: React and Vite frontend

- Status: accepted
- Decision: use React, strict TypeScript, Vite, React Router, TanStack Query, Recharts, Vitest, React Testing Library, and Playwright.
- Rationale: a portable browser client with a small, well-supported toolchain and explicit separation between server state, view models, and components.
- Consequence: production output is static and can be served by any standards-compliant web server; Node.js is a build dependency, not an end-user requirement.
