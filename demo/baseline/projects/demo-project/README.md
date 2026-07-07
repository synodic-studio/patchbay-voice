# Widget Store API

A small FastAPI service for a toy widget store. It is the sample project for the
Patchbay Voice demo: talk to the assistant and watch it read this code and take
notes for you.

## Features

- List all widgets, or fetch a single widget by ID
- Create a new widget and delete an existing one
- In-memory storage, so there is no database to set up

## Setup

Install dependencies with `uv sync`, then start the server with
`uv run uvicorn main:app`. It listens on port 8000.

## Usage

- `GET /widgets` returns every widget
- `GET /widgets/{id}` returns one widget
- `POST /widgets` creates a widget from a name
- `DELETE /widgets/{id}` removes one

## Roadmap

- Persistent storage instead of an in-memory dict
- Search and filtering on the list endpoint
- Simple token authentication
