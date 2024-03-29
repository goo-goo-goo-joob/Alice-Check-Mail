PROJECT_NAME ?= alice_api
VERSION = $(shell python3 setup.py --version | tr '+' '-')
PROJECT_NAMESPACE ?= mlao
REGISTRY_IMAGE ?= $(PROJECT_NAMESPACE)/$(PROJECT_NAME)

all:
	@echo "make clean			- Remove files created by distutils"
	@echo "make sdist			- Make source distribution"
	@echo "make pyinstall		- Install package localy"
	@echo "make docker			- Build a docker image"
	@echo "make docker_start	- Up docker compose"
	@echo "make docker_all		- Build & Up docker compose"
	@echo "make docker_logs		- View docker compose logs"
	@exit 0

clean:
	rm -fr *.egg-info dist

sdist: clean
	python3 setup.py sdist

pyinstall:clean
	python3 setup.py build
	python3 setup.py install

docker: sdist
	docker build -t $(PROJECT_NAME):$(VERSION) .

docker_start:
	docker tag $(PROJECT_NAME):$(VERSION) $(REGISTRY_IMAGE):$(VERSION)
	docker tag $(PROJECT_NAME):$(VERSION) $(REGISTRY_IMAGE):latest
	docker-compose up -d

docker_all:docker docker_start

docker_logs:
	docker-compose logs