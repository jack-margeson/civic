FROM postgres:latest
WORKDIR /docker-entrypoint-initdb.d/
COPY . .
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["postgres"]