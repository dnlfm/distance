.PHONY: setup
setup:
	@mkdir -p ./nominatim_data
	@echo "Created ./nominatim_data"
	@echo
	@echo "Please download the Sudeste OSM PBF and place it into ./nominatim_data:"
	@echo "  https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf"
	@echo
	@echo "On Linux/macOS you can run:"
	@echo "  wget -P ./nominatim_data https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf"
	@echo
	@echo "On Windows (PowerShell) you can run:"
	@echo "  Invoke-WebRequest -OutFile .\nominatim_data/sudeste-latest.osm.pbf -Uri https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf"
	@echo
	@echo "After placing the file, start the stack with:"
	@echo "  docker-compose up -d"
	@echo
	@echo "Note: OSRM and Nominatim preprocessing can take a long time. Monitor container logs and be patient."
	@echo "When you see: 'running and waiting for requests' then it should be able to accept requests."