#!/bin/bash

# CascadeS2S Management Script
# Provides an easy way to manage the real-time voice agent application.

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    echo "Usage: ./manage.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start       Build and start all services in detached mode"
    echo "  stop        Stop all running services"
    echo "  restart     Restart all services"
    echo "  logs        Follow logs for all services"
    echo "  status      Show status of all services"
    echo "  clean       Stop services and remove containers, networks, and images"
    echo "  pull-llm    Manually trigger Ollama to pull the Qwen 2.5 model"
    echo "  help        Show this help message"
}

# Check for docker-compose command availability
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}Error: docker-compose or docker compose not found.${NC}"
    exit 1
fi

case "$1" in
    start)
        echo -e "${GREEN}Starting CascadeS2S services...${NC}"
        $DOCKER_COMPOSE up --build -d
        echo -e "${GREEN}Application is starting at http://localhost:8000${NC}"
        ;;
    stop)
        echo -e "${GREEN}Stopping CascadeS2S services...${NC}"
        $DOCKER_COMPOSE stop
        ;;
    restart)
        echo -e "${GREEN}Restarting CascadeS2S services...${NC}"
        $DOCKER_COMPOSE restart
        ;;
    logs)
        $DOCKER_COMPOSE logs -f
        ;;
    status)
        $DOCKER_COMPOSE ps
        ;;
    clean)
        echo -e "${RED}Warning: This will remove containers, networks, and images.${NC}"
        read -p "Are you sure? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            $DOCKER_COMPOSE down --rmi all --volumes --remove-orphans
        fi
        ;;
    pull-llm)
        echo -e "${GREEN}Triggering model pull for Qwen 2.5:3b...${NC}"
        docker exec -it ollama ollama pull qwen2.5:3b
        ;;
    help|*)
        show_usage
        ;;
esac
