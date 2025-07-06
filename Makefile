build:
	docker compose build
	docker compose down
run:
	docker compose up --watch
logs:
	docker compose logs -f