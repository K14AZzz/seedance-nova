#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = "https://llm-proxy.tapsvc.com"
DEFAULT_MODEL = "doubao-seedance-2-0-fast-260128"
DEFAULT_RATIO = "16:9"
DEFAULT_RESOLUTION = "480p"
DEFAULT_DURATION = 4
DEFAULT_POLL_SECONDS = 10
TERMINAL_STATES = {"succeeded", "failed", "cancelled", "canceled"}
CONFIG_PATH = Path.home() / ".config" / "seedance-nova" / "config.json"


def load_config():
    config = {}
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text())
    return {
        "base_url": os.environ.get("NOVA_BASE_URL")
        or config.get("base_url")
        or DEFAULT_BASE_URL,
        "api_key": os.environ.get("NOVA_LLM_API_KEY")
        or os.environ.get("SEEDANCE_API_KEY")
        or config.get("api_key"),
        "default_model": config.get("default_model") or DEFAULT_MODEL,
        "default_ratio": config.get("default_ratio") or DEFAULT_RATIO,
        "default_resolution": config.get("default_resolution") or DEFAULT_RESOLUTION,
        "default_duration": int(config.get("default_duration") or DEFAULT_DURATION),
        "default_generate_audio": bool(config.get("default_generate_audio", False)),
    }


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")


def build_url(base_url, path):
    return base_url.rstrip("/") + path


def request_json(method, url, api_key, payload=None, timeout=60):
    headers = {"Authorization": f"Bearer {api_key}"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} calling {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error calling {url}: {exc}") from exc


def download_file(url, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as resp:
        output.write_bytes(resp.read())
    return output


def ensure_api_key(config):
    if not config.get("api_key"):
        raise SystemExit(
            "Missing API key. Set NOVA_LLM_API_KEY or run `seedance.py init --api-key ...`."
        )


def task_state(task):
    return (task.get("status") or task.get("state") or task.get("task_status") or "").lower()


def create_task(config, args):
    payload = {
        "model": args.model or config["default_model"],
        "content": [{"type": "text", "text": args.prompt}],
        "resolution": args.resolution or config["default_resolution"],
        "ratio": args.ratio or config["default_ratio"],
        "duration": args.duration or config["default_duration"],
        "generate_audio": args.audio,
    }
    return request_json(
        "POST",
        build_url(config["base_url"], "/volcengine/api/v3/contents/generations/tasks"),
        config["api_key"],
        payload,
        timeout=args.timeout,
    )


def fetch_task(config, task_id, timeout=60):
    quoted = urllib.parse.quote(task_id, safe="")
    return request_json(
        "GET",
        build_url(config["base_url"], f"/volcengine/api/v3/contents/generations/tasks/{quoted}"),
        config["api_key"],
        timeout=timeout,
    )


def wait_for_task(config, task_id, poll_seconds, timeout_seconds):
    started = time.time()
    while True:
        task = fetch_task(config, task_id, timeout=min(60, poll_seconds + 10))
        state = task_state(task)
        print(state or "unknown", file=sys.stderr)
        if state in TERMINAL_STATES:
            return task
        if time.time() - started > timeout_seconds:
            raise SystemExit(f"Timed out waiting for task {task_id}")
        time.sleep(poll_seconds)


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_init(config, args):
    next_config = {
        "base_url": args.base_url or config["base_url"],
        "api_key": args.api_key or config.get("api_key"),
        "default_model": args.model or config["default_model"],
        "default_ratio": args.ratio or config["default_ratio"],
        "default_resolution": args.resolution or config["default_resolution"],
        "default_duration": args.duration or config["default_duration"],
        "default_generate_audio": args.audio,
    }
    if not next_config["api_key"]:
        raise SystemExit("init requires --api-key when no saved key exists.")
    save_config(next_config)
    print(f"Saved config to {CONFIG_PATH}")


def cmd_probe(config, _args):
    ensure_api_key(config)
    data = request_json(
        "GET",
        build_url(config["base_url"], "/v1/models"),
        config["api_key"],
        timeout=30,
    )
    ids = [item.get("id", "") for item in data.get("data", []) if isinstance(item, dict)]
    hits = [mid for mid in ids if "seedance" in mid.lower()]
    print_json(
        {
            "base_url": config["base_url"],
            "seedance_models": hits,
            "configured": bool(config.get("api_key")),
        }
    )


def cmd_submit(config, args):
    ensure_api_key(config)
    result = create_task(config, args)
    print_json(result)


def cmd_status(config, args):
    ensure_api_key(config)
    print_json(fetch_task(config, args.task_id, timeout=args.timeout))


def cmd_download(config, args):
    ensure_api_key(config)
    task = fetch_task(config, args.task_id, timeout=args.timeout)
    video_url = ((task.get("content") or {}).get("video_url"))
    if not video_url:
        raise SystemExit(f"Task {args.task_id} has no video_url yet.")
    output = download_file(video_url, args.output)
    print(output)


def cmd_generate(config, args):
    ensure_api_key(config)
    created = create_task(config, args)
    task_id = created.get("id")
    if not task_id:
        raise SystemExit(f"Task creation returned no id: {created}")
    print_json(created)
    task = wait_for_task(config, task_id, args.poll_seconds, args.wait_timeout)
    if task_state(task) != "succeeded":
        print_json(task)
        raise SystemExit(f"Task {task_id} ended with state {task_state(task)}")
    video_url = ((task.get("content") or {}).get("video_url"))
    if args.output and video_url:
        output = download_file(video_url, args.output)
        task["downloaded_to"] = str(output)
    print_json(task)


def parser():
    p = argparse.ArgumentParser(description="Seedance 2.0 helper via Nova Volcengine passthrough")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Save local config")
    init.add_argument("--api-key")
    init.add_argument("--base-url", default=DEFAULT_BASE_URL)
    init.add_argument("--model", default=DEFAULT_MODEL)
    init.add_argument("--ratio", default=DEFAULT_RATIO)
    init.add_argument("--resolution", default=DEFAULT_RESOLUTION)
    init.add_argument("--duration", type=int, default=DEFAULT_DURATION)
    init.add_argument("--audio", action="store_true", default=False)

    sub.add_parser("probe", help="Check gateway and available Seedance models")

    submit = sub.add_parser("submit", help="Create a Seedance task")
    submit.add_argument("--prompt", required=True)
    submit.add_argument("--model")
    submit.add_argument("--ratio")
    submit.add_argument("--resolution")
    submit.add_argument("--duration", type=int)
    submit.add_argument("--audio", action="store_true", default=False)
    submit.add_argument("--timeout", type=int, default=60)

    status = sub.add_parser("status", help="Fetch task status")
    status.add_argument("task_id")
    status.add_argument("--timeout", type=int, default=60)

    download = sub.add_parser("download", help="Download a finished video")
    download.add_argument("task_id")
    download.add_argument("--output", required=True)
    download.add_argument("--timeout", type=int, default=60)

    generate = sub.add_parser("generate", help="Create, wait, and optionally download")
    generate.add_argument("--prompt", required=True)
    generate.add_argument("--model")
    generate.add_argument("--ratio")
    generate.add_argument("--resolution")
    generate.add_argument("--duration", type=int)
    generate.add_argument("--audio", action="store_true", default=False)
    generate.add_argument("--timeout", type=int, default=60)
    generate.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    generate.add_argument("--wait-timeout", type=int, default=1800)
    generate.add_argument("--output")

    return p


def main():
    args = parser().parse_args()
    config = load_config()
    handlers = {
        "init": cmd_init,
        "probe": cmd_probe,
        "submit": cmd_submit,
        "status": cmd_status,
        "download": cmd_download,
        "generate": cmd_generate,
    }
    handlers[args.command](config, args)


if __name__ == "__main__":
    main()
