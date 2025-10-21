.PHONY: setup
setup:
	@mkdir -p ./nominatim_data
	@echo "Created ./nominatim_data"
	@echo
	# Copy .env.example to .env if .env doesn't already exist
	@if [ -f .env.example ] && [ ! -f .env ]; then \
	  cp .env.example .env; \
	  echo "Copied .env.example -> .env"; \
	elif [ -f .env ]; then \
	  echo ".env already exists, skipping copy"; \
	else \
	  echo ".env.example not found, skipping .env creation"; \
	fi
	@echo
	@echo "Attempting to download sudeste-latest.osm.pbf automatically on Linux or macOS if a downloader is available..."
	@unameOut=$$(uname -s 2>/dev/null || echo Unknown); \
	URL="https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf"; \
	echo "Detected $$unameOut. Checking for download tools..."; \
	FNAME=$$(basename "$$URL"); \
	if [ "$$unameOut" = "Linux" ] || [ "$$unameOut" = "Darwin" ]; then \
	  if [ -f ./nominatim_data/"$$FNAME" ]; then \
	    echo "File ./nominatim_data/$$FNAME already exists, skipping download"; \
	  else \
	    if [ "$$unameOut" = "Linux" ] && command -v wget >/dev/null 2>&1; then \
	      echo "Downloading with wget to ./nominatim_data/"; \
	      wget -c -P ./nominatim_data "$$URL"; \
	    elif [ "$$unameOut" = "Linux" ] && command -v curl >/dev/null 2>&1; then \
	      echo "wget not found, using curl instead"; \
	      curl -L -o ./nominatim_data/"$$FNAME" "$$URL"; \
	    elif [ "$$unameOut" = "Darwin" ] && command -v curl >/dev/null 2>&1; then \
	      echo "Downloading with curl to ./nominatim_data/"; \
	      curl -L -o ./nominatim_data/"$$FNAME" "$$URL"; \
	    elif [ "$$unameOut" = "Darwin" ] && command -v wget >/dev/null 2>&1; then \
	      echo "curl not found, using wget instead"; \
	      wget -c -P ./nominatim_data "$$URL"; \
	    else \
	      echo "Neither curl nor wget available. Please download manually:"; \
	      echo "  $$URL"; \
	    fi; \
	  fi; \
	else \
	  echo "Automatic download only attempted on Linux/macOS. Please download manually as needed:"; \
	  echo "  curl -L -o ./nominatim_data/sudeste-latest.osm.pbf $$URL"; \
	  echo; \
	  echo "Or on systems with wget:"; \
	  echo "  wget -P ./nominatim_data $$URL"; \
	fi
	@echo
	@echo "After placing the file, start the stack with:"
	@echo "  docker-compose up -d"
	@echo
	@echo "Note: OSRM and Nominatim preprocessing can take a long time. Monitor container logs and be patient."
	@echo "When you see: 'running and waiting for requests' then it should be able to accept requests."
