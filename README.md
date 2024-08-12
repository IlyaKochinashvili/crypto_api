FastAPI Crypto Price API
This FastAPI application retrieves real-time cryptocurrency price data from Kraken and Binance exchanges using WebSockets. The application normalizes trading pairs across exchanges and provides an API to query the data.

Prerequisites
Docker
Docker Compose

Getting Started
1. Clone the Repository
bash

git clone https://github.com/IlyaKochinashvili/crypto_api.git

cd fastapi-crypto-api

2. Build and Run the Docker Containers
To build and start the application, use Docker Compose:

bash

docker-compose up --build

This will build the Docker image and start the containers for the application. The FastAPI application will be available at http://127.0.0.1:8000.

3. Example Usage
You can query the API for prices using the following endpoint:

bash

http://127.0.0.1:8000/prices/?pair=ETHUSDT&exchange=kraken

This will return the current bid, ask, and average prices for the ETHUSDT trading pair on the Kraken exchange.

