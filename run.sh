echo "=== Setting up Docker containers ==="
docker compose -f docker/docker-compose.cpu.yaml up -d

echo "=== Starting ImageGeneratorsHub (port 8001) ==="
uvicorn main:app --app-dir ./ImageGeneratorsHub-main --host 0.0.0.0 --port 8001 &
IMG_PID=$!

echo "=== Starting Needle Backend (port 8000) ==="

echo "Choose configuration mode for Needle backend:"
select config_mode in "fast" "balanced" "accurate"; do
  case $config_mode in
    fast|balanced|accurate)
      export SERVICE__CONFIG_DIR_PATH="./configs/$config_mode"
      break
      ;;
    *)
      echo "Invalid selection. Please choose 1 (fast), 2 (balanced), or 3 (accurate)."
      ;;
  esac
done

uvicorn main:app --app-dir ./backend/ --host 0.0.0.0 --port 8000 &
NEEDLE_PID=$!

# Trap CTRL+C to cleanly stop both apps
trap "echo -e '\nStopping servers...'; kill $IMG_PID $NEEDLE_PID; exit" SIGINT

# Wait for both to exit (blocks script)
wait
