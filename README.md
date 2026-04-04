---
title: HospitRL
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
tags:
- openenv
---

# HospitRL Environment

An OpenEnv compliant reinforcement learning environment for hospital ward management.

## Setup and Usage
This environment runs in a Docker container. It exposes a FastAPI server on port 7860.
- POST /reset : Resets the hospital
- POST /step : Executes a staff move
- GET /health : Checks server status

## Action Space
- source_ward: Integer (0-2)
- target_ward: Integer (0-2)
- staff_count: Integer (Number of staff to move)