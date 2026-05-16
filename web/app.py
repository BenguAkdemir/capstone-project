"""Flask UI — manual input, weekly schedule, database sync."""

from __future__ import annotations

import requests
from flask import Flask, jsonify, render_template, request

from config import BACKEND_URL, REQUEST_TIMEOUT

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/planning")
def get_planning():
    try:
        resp = requests.get(f"{BACKEND_URL}/employees/planning", timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not reach backend: {exc}"}), 502
    try:
        body = resp.json()
    except ValueError:
        body = {"error": resp.text[:500]}
    return jsonify(body), resp.status_code


@app.post("/api/employees/sync")
def sync_employees():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "No data sent"}), 400
    try:
        resp = requests.post(
            f"{BACKEND_URL}/employees/sync",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not reach backend: {exc}"}), 502
    try:
        body = resp.json()
    except ValueError:
        body = {"error": resp.text[:500]}
    return jsonify(body), resp.status_code


@app.post("/api/optimize")
def optimize():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "No data sent"}), 400
    try:
        resp = requests.post(
            f"{BACKEND_URL}/schedule",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        return jsonify({"error": "Request timed out. Please try again later."}), 504
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not reach server: {exc}"}), 502
    try:
        body = resp.json()
    except ValueError:
        body = {"error": resp.text[:500]}
    return jsonify(body), resp.status_code


@app.get("/health")
def health():
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return jsonify({"web": "ok", "backend": r.json()}), 200
    except requests.RequestException as exc:
        return jsonify({"web": "ok", "backend": str(exc)}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
