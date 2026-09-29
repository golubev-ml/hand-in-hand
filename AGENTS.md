# figma-make-app

React + Vite + Tailwind CSS project running inside Figma Make.

## Development Server

A Vite development server is **already running** on `$PORT` (default 8443). You don't need to start it manually.

- Preview URL: The user can access the running app through the preview panel
- Hot reload: Changes to source files are reflected immediately

## Project Structure

This is the canonical project structure. Start with task-relevant files below. Only follow imports or inspect other files when required, when a documented path is missing, or when the repository contradicts this guide.

- `src/main.tsx` - React entrypoint; imports `src/index.css` and mounts `src/App.tsx` into the `#root` element
- `src/App.tsx` - Primary application component and the usual starting point for UI work
- `src/index.css` - Global CSS entrypoint and Tailwind CSS v4 import
- `index.html` - Vite HTML shell containing the `#root` element and loading `src/main.tsx`
- `package.json` - Project dependencies and the Vite build, development, preview, and formatting scripts
- `vite.config.ts` - Vite configuration with React, Tailwind CSS v4, and Figma Make plugins plus the `@` alias for `src`
- `.mise.toml` - Toolchain versions for Node.js and pnpm

## Dependencies

- Runtime: React 19 and React DOM 19
- Styling: Tailwind CSS v4 with the `@tailwindcss/vite` plugin
- Build tooling: Vite 8, TypeScript 5.7, and `@vitejs/plugin-react`
- Formatting: oxfmt

## Styling

This project uses **Tailwind CSS v4** through the `@tailwindcss/vite` plugin configured in `vite.config.ts`. `src/index.css` imports Tailwind with `@import 'tailwindcss';`. Use Tailwind utility classes directly in JSX and put global CSS or Tailwind v4 theme customization in `src/index.css`. This scaffold does not need a Tailwind config file or PostCSS config.

`src/main.tsx` imports `src/index.css`, so global font wiring belongs in `src/index.css`. Keep CSS `@import` statements first, then add any `@font-face` rules and font-family defaults there.

## Code quality

- Use double quotes for strings containing apostrophes (`"We're here to help"`), or escape them in single-quoted strings. An unescaped apostrophe in a single-quoted string breaks the build.
- Ensure JSX tags are closed and braces are balanced.
- Export components as default exports.

## Deployment proxy

- Production Docker requires API `1.44` or newer. Keep
  `DOCKER_API_VERSION: "1.44"` on the bundled Traefik service in
  `deploy/docker-compose.yml`; never restore the legacy `1.24`/`1.40` values.
- Before changing the Traefik image or Docker API version, check the server's
  minimum API with `docker version`. A running container is not sufficient:
  verify that Traefik has loaded the Docker provider without API-version errors.
- After proxy changes, verify `/`, `/api/health`, `/admin`, and the landing
  domain over HTTPS and inspect the Traefik logs.

## Deployment build cache

- Docker layer cache on the servers is intentional: it preserves the completed
  `pip install` and `npm ci` layers and makes normal repeat deployments fast.
  Do not run `docker builder prune -af` or an unscoped Docker cleanup as part
  of deployment.
- Before deployment, check free space with `df -h /` and cache usage with
  `docker system df`. If disk space is genuinely low, inspect candidates first
  and remove only clearly obsolete images or caches; retain the dependency
  layers used by `deploy-api` and `deploy-frontend`.
