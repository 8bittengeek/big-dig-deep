
Development clean; use `docker compose down` before `docker compose up --build` to ensure a clean slate

Full clean and restart development
```
docker ps -a
docker rm -f archive-qapp archive-backend
docker system prune -f
docker compose up --build
```
