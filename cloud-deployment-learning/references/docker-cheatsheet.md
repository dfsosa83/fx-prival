# Docker — Common Commands

## Image Management

```bash
# Build an image from a Dockerfile in the current directory
docker build -t my-image .

# Build from a specific Dockerfile
docker build -t my-image -f Dockerfile.frival .

# List all images on your machine
docker images

# Delete an image
docker rmi my-image

# Delete all unused images (dangling + unreferenced)
docker image prune -a
```

## Container Management

```bash
# Run a container from an image
docker run my-image

# Run interactively (bash shell inside container)
docker run -it my-image /bin/bash

# Run in background (detached)
docker run -d my-image

# Map a host port to a container port
docker run -p 8000:8000 my-image

# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# View logs of a container
docker logs <container-id>

# Stop a running container
docker stop <container-id>

# Remove a stopped container
docker rm <container-id>

# Stop and remove all containers
docker rm -f $(docker ps -aq)
```

## Dockerfile Instructions

| Instruction | What It Does |
|---|---|
| `FROM python:3.11-slim` | Base image (start here) |
| `WORKDIR /app` | Set working directory for subsequent commands |
| `COPY requirements.txt .` | Copy file from host to image |
| `RUN pip install -r requirements.txt` | Execute command during build |
| `CMD ["python", "main.py"]` | Default command when container starts |
| `ENTRYPOINT ["python"]` | Fixed executable (CMD becomes its arguments) |
| `ENV PYTHONUNBUFFERED=1` | Set environment variable |
| `EXPOSE 8000` | Document which port the app listens on (informational only) |

## Troubleshooting

```bash
# Get a shell inside a RUNNING container
docker exec -it <container-id> /bin/bash

# Inspect image layers and their sizes
docker history my-image

# See what changed in a container's filesystem
docker diff <container-id>

# Prune everything (images, containers, volumes, networks not in use)
docker system prune -a
```