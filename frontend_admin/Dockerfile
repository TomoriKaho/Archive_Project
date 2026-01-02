FROM node:20-slim

WORKDIR /app/frontend_admin

COPY frontend_admin/package.json frontend_admin/package-lock.json ./
RUN npm ci

COPY frontend_admin/ ./
COPY frontend_shared/ /app/frontend_shared/

EXPOSE 8080

CMD ["npm", "run", "serve", "--", "--host", "0.0.0.0", "--port", "8080", "--disable-host-check"]
