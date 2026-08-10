# Trip Agent AI

Trip Agent AI is a web application that generates a complete travel plan from a single natural-language request. A user describes a trip (for example, "Plan a 7 day trip to Japan from India under a moderate budget"), and the system searches for live flight information, looks up hotel options, and produces a day-by-day itinerary and final travel recommendation using a large language model.

The backend is built as a multi-agent workflow using LangGraph, exposed through a FastAPI web server, with a browser-based frontend served from the same application.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Getting the Required API Keys](#getting-the-required-api-keys)
- [Local Setup](#local-setup)
- [Running with Docker](#running-with-docker)
- [API Reference](#api-reference)
- [Known Limitations](#known-limitations)
- [License](#license)

## Overview

Given a single message from the user, the application performs the following steps automatically:

1. Interprets the request and extracts trip details (origin, destination, dates, budget, and similar information) as needed.
2. Looks up live flight data for the identified route.
3. Searches the web for relevant hotel options.
4. Uses a language model to draft a day-by-day itinerary based on the flight and hotel information.
5. Uses a language model to produce a final, formatted travel recommendation combining all of the above.

Each conversation is tracked with a `thread_id` and persisted in a PostgreSQL database, so a session can be resumed or inspected later.

## How It Works

The core logic lives in [backend.py](backend.py) and is implemented as a state graph using LangGraph. The workflow consists of four sequential agents (nodes), each of which updates a shared state object:

```
START -> flight_agent -> hotel_agent -> itinerary_agent -> final_agent -> END
```

- **flight_agent**: Parses the user's request to identify departure and arrival locations, resolves them to airport codes, and queries the AviationStack API for live flight data (see [Tools/flight_tool.py](Tools/flight_tool.py)).
- **hotel_agent**: Builds a hotel-focused search query and retrieves web search results using the Tavily search API (see [Tools/tavily_tool.py](Tools/tavily_tool.py)).
- **itinerary_agent**: Sends the flight results, hotel results, and original request to a language model (via Groq) and asks it to draft a practical itinerary.
- **final_agent**: Sends the full context to the language model again and asks it to produce a polished, sectioned final response (trip summary, flight information, hotel suggestions, itinerary, estimated budget, and recommendations).

State for each conversation is checkpointed to PostgreSQL using `langgraph-checkpoint-postgres`, which allows a given `thread_id` to be continued across multiple requests.

The FastAPI application in [app.py](app.py) exposes this workflow over HTTP and serves a static HTML/CSS/JavaScript frontend (see [templates/index.html](templates/index.html), [static/script.js](static/script.js), and [static/style.css](static/style.css)) that lets a user submit a request and view the generated plan in the browser.

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI, served by Uvicorn |
| Agent orchestration | LangGraph |
| LLM integration | LangChain, langchain-groq (Groq-hosted LLaMA model) |
| Web search | Tavily Search API |
| Flight data | AviationStack API |
| Persistence | PostgreSQL, accessed via psycopg |
| Templating | Jinja2 |
| Frontend | HTML, CSS, and vanilla JavaScript |
| Containerization | Docker |

## Project Structure

```
TripAgent/
├── app.py                 FastAPI application: HTTP routes and server entry point
├── backend.py              LangGraph workflow definition and agent logic
├── test.py                 Command-line script for exercising the workflow manually
├── requirements.txt        Python dependencies
├── Dockerfile               Container build definition
├── Tools/
│   ├── flight_tool.py        Flight search and airport/location resolution logic
│   └── tavily_tool.py        Hotel/web search logic via the Tavily API
├── templates/
│   └── index.html            Main HTML page served to the browser
├── static/
│   ├── script.js              Frontend logic (form handling, API calls, rendering)
│   └── style.css               Frontend styling
└── LICENSE
```

## Prerequisites

- Python 3.11 or later
- A PostgreSQL database (a free hosted instance, such as one from Render, is sufficient)
- API keys for the following services:
  - Groq (language model access)
  - Tavily (web search)
  - AviationStack (flight data)

## Environment Variables

The application reads its configuration from environment variables, typically supplied via a `.env` file in the project root during local development. Create a file named `.env` with the following keys:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string used for workflow checkpointing. If `sslmode` is not included, the application appends `sslmode=require` automatically. |
| `GROQ_API_KEY` | Yes | API key for the Groq-hosted language model used to generate itineraries and final responses. |
| `TAVILY_API_KEY` | Yes | API key for the Tavily search API, used to retrieve hotel and general travel information. |
| `AVIATIONSTACK_API_KEY` | Yes | API key for the AviationStack API, used to retrieve live flight data. |
| `DEFAULT_ORIGIN_IATA` | No | Fallback departure airport IATA code used when a request only specifies a destination. Defaults to `JFK`. |

The application will raise an error at startup if `DATABASE_URL` or `GROQ_API_KEY` is missing. Requests that depend on `TAVILY_API_KEY` or `AVIATIONSTACK_API_KEY` will return a descriptive error message if those keys are not configured, rather than failing the entire application.

The `.env` file must never be committed to version control. It is excluded via `.gitignore` and `.dockerignore` in this repository.

## Getting the Required API Keys

- **Groq**: Create an account and generate an API key at the Groq console.
- **Tavily**: Create an account and generate an API key at the Tavily website.
- **AviationStack**: Create an account and generate an API key at the AviationStack website. The free tier provides live flight status data, not ticket pricing.
- **PostgreSQL**: Any standard PostgreSQL provider works. A free managed instance (for example, from Render or Supabase) is sufficient for development and testing.

## Local Setup

1. Clone the repository and move into the project directory:

   ```bash
   git clone <repository-url>
   cd TripAgent
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root as described in [Environment Variables](#environment-variables).

5. Start the application:

   ```bash
   python app.py
   ```

   This starts the server at `http://127.0.0.1:8000` with auto-reload enabled. Alternatively, run it directly with Uvicorn:

   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

6. Open `http://127.0.0.1:8000` in a browser to use the application.

You can also test the workflow directly from the command line, without the web server, using:

```bash
python test.py
```

## Running with Docker

A `Dockerfile` is provided to run the application in a container.

1. Build the image:

   ```bash
   docker build -t trip-agent-ai .
   ```

2. Run the container, passing environment variables from your local `.env` file:

   ```bash
   docker run --env-file .env -p 8000:8000 trip-agent-ai
   ```

3. Open `http://localhost:8000` in a browser.

The `.env` file is excluded from the image build via `.dockerignore`; environment variables must be supplied at runtime, either with `--env-file` as shown above or through the configuration mechanism of your hosting platform.

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves the main HTML page. |
| `POST` | `/api/travel` | Accepts a travel request and returns the generated plan. |
| `GET` | `/health` | Returns a simple health check response. |

### `POST /api/travel`

Request body:

```json
{
  "message": "Plan a 5 day trip to Dubai from Delhi under a moderate budget",
  "thread_id": null
}
```

- `message` (string, required): The natural-language travel request.
- `thread_id` (string, optional): An identifier used to continue a previous conversation. If omitted, a new one is generated automatically.

Successful response (`200 OK`):

```json
{
  "success": true,
  "thread_id": "user_...",
  "answer": "Formatted final travel recommendation",
  "flight_results": "Formatted flight search results",
  "hotel_results": "Formatted hotel search results",
  "itinerary": "Generated itinerary text",
  "llm_calls": 2
}
```

Error response (`400` or `500`):

```json
{
  "success": false,
  "error": "Description of the error"
}
```

## Known Limitations

- AviationStack's free tier provides live flight status information, not ticket prices. The generated response notes this limitation where relevant.
- Location parsing in [Tools/flight_tool.py](Tools/flight_tool.py) relies on pattern matching and a curated list of city, country, and airport mappings, and may not correctly resolve every possible phrasing of an origin or destination.
- The application requires a reachable PostgreSQL database at startup; it will not start if `DATABASE_URL` is missing or invalid.

## License

This project is licensed under the terms of the [MIT License](LICENSE).
