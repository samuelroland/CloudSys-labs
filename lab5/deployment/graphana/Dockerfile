# Utilise l'image officielle Grafana comme base
FROM grafana/grafana:latest

# Installe le plugin Redis Data Source
RUN grafana-cli plugins install redis-datasource

# Optionnel : on peut marquer que l'image a été modifiée
LABEL maintainer="olivia.manz@master.hes-so.ch"
