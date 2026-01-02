FROM node:20-slim

WORKDIR /app/frontend_client

COPY frontend_client/package.json frontend_client/package-lock.json ./
RUN npm ci

COPY frontend_client/ ./
COPY frontend_shared/ /app/frontend_shared/

EXPOSE 8081

CMD ["npm", "run", "serve", "--", "--host", "0.0.0.0", "--port", "8081", "--disable-host-check"]
