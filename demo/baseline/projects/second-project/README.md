# Trailhead

A small command-line tool that turns a folder of GPX tracks into a summary of
your hikes. This second sample project exists so you can try starting a new
session from the sessions list.

## Features

- Parse one or many GPX files
- Report total distance, elevation gain, and moving time
- Export the summary as CSV

## Setup

Install with `uv sync`, then run `uv run trailhead ./tracks`.

## Roadmap

- Detect and merge paused segments
- Per-hike pace charts
- A simple web view of the summary
