FROM node:20-alpine AS build
WORKDIR /web
ENV NODE_OPTIONS=--max_old_space_size=4096
COPY web/ .
RUN npm install --registry=https://registry.npmmirror.com --no-audit --no-fund --legacy-peer-deps
RUN npm run build

FROM nginx:alpine
COPY docker_env/nginx/my.conf /etc/nginx/conf.d/my.conf
COPY --from=build /web/dist /usr/share/nginx/html
