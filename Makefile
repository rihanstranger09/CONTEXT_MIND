.PHONY: test compose-up compose-down images k8s-apply helm-lint helm-render

test:
	python -m pytest -q

compose-up:
	docker compose up --build

compose-down:
	docker compose down

images:
	docker build -t scalable-app-backend:latest ./backend
	docker build -t scalable-app-frontend:latest ./frontend

k8s-apply:
	kubectl apply -f k8s/

helm-lint:
	helm lint ./scalable-app-chart

helm-render:
	helm template task-demo ./scalable-app-chart
