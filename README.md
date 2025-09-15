# Bitcoin Solo Miner Monitoring App

A comprehensive monitoring application for Bitcoin solo miners, supporting multiple miner types including Bitaxe, Avalon Nano, and Magic Miner.

## Dependencies

### Python Backend Dependencies

The Python backend requires the following packages (see `requirements.txt`):

- **FastAPI** (0.104.*) - Modern web framework for building APIs
- **Uvicorn** (0.24.*) - ASGI server for FastAPI
- **aiohttp** (3.9.*) - Async HTTP client for miner communication
- **aiosqlite** (0.19.*) - Async SQLite database interface
- **influxdb-client** (1.38.*) - InfluxDB client for time-series data
- **PyJWT** (2.8.*) - JSON Web Token implementation
- **pydantic** (2.5.*) - Data validation using Python type annotations
- **bcrypt** (4.1.*) - Password hashing library
- **psutil** (5.9.*) - System and process monitoring
- **beautifulsoup4** (4.12.*) - HTML parsing for Magic Miner web scraping
- **websockets** (12.0) - WebSocket support
- **pytest** (7.4.*) - Testing framework

### Frontend Dependencies

The Vue.js frontend requires the following packages (see `src/frontend/package.json`):

- **Vue.js** (^3.3.8) - Progressive JavaScript framework
- **Vue Router** (^4.2.5) - Official router for Vue.js
- **Pinia** (^2.1.7) - State management for Vue.js
- **Vuetify** (^3.4.4) - Material Design component framework
- **Axios** (^1.6.2) - HTTP client for API communication
- **Chart.js** (^4.4.0) - Charting library
- **Vue Chart.js** (^5.2.0) - Vue.js wrapper for Chart.js

## Installation

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python src/main.py
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd src/frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
```

## Development

### Backend Development

The backend is built with FastAPI and uses:
- SQLite for configuration storage
- InfluxDB for time-series metrics data
- Async/await patterns for non-blocking operations
- WebSocket for real-time updates

### Frontend Development

The frontend is built with Vue.js 3 and uses:
- Composition API for reactive state management
- Vuetify for Material Design components
- Pinia for state management
- Vite for fast development and building

## Architecture

The application follows a modern async architecture:
- **Backend**: FastAPI with async database operations
- **Frontend**: Vue.js 3 with Composition API
- **Communication**: REST API + WebSocket for real-time updates
- **Data Storage**: SQLite + InfluxDB for different data types

## Supported Miners

- **Bitaxe**: HTTP API-based communication
- **Avalon Nano**: Socket-based CGMiner API
- **Magic Miner**: Web scraping-based data extraction