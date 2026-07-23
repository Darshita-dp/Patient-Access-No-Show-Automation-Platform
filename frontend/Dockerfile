# React frontend for the Patient Access & No-Show Automation Platform.
#
# Runs the Vite dev server so the reviewer flow (`docker compose up --build`)
# is a single command: no separate build step, live source edits reload
# automatically if they mount src/. The image itself is production-safe —
# for a real deploy, swap the CMD for `npm run build` + an nginx layer.

FROM node:20-slim

ENV NODE_ENV=development \
    CI=true

WORKDIR /app

# Copy the manifest and lockfile first so a source change doesn't
# invalidate the dependency layer.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# Vite must bind 0.0.0.0 inside the container to be reachable from the host.
# The frontend reads VITE_API_URL at build time; docker-compose sets it to
# http://localhost:8000 which resolves in the *browser* (the container is
# never the one talking to the API — that's the point of the SPA).
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
