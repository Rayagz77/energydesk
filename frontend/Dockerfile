# syntax=docker/dockerfile:1
# Front-end EnergyDesk : fichiers statiques servis par Nginx en utilisateur non privilegie
# (image nginx-unprivileged : port 8080, utilisateur nginx uid 101).
# Pas d'etape de build (HTML/CSS/JS natifs) : une seule etape suffit, l'image reste legere.
ARG NGINX_IMAGE=nginxinc/nginx-unprivileged:stable-alpine
FROM ${NGINX_IMAGE}
LABEL org.opencontainers.image.title="energydesk-frontend" \
      org.opencontainers.image.source="https://github.com/rayagz77/energydesk"
ENV API_UPSTREAM=api:8000
USER root
RUN rm -f /etc/nginx/conf.d/default.conf && mkdir -p /etc/nginx/snippets
COPY nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY src/ /usr/share/nginx/html/
RUN chmod -R a+rX /usr/share/nginx/html /etc/nginx/snippets
USER 101
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
