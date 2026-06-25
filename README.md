# seedance-nova

Reusable Codex skill for generating Seedance 2.0 videos through Nova AI Gateway's Volcengine passthrough.

## What it does

- probes visible Seedance models from `https://llm-proxy.tapsvc.com/v1/models`
- submits async Seedance 2.0 video tasks
- polls task status
- downloads finished videos

This skill intentionally does **not** use `fal` or OpenAI video endpoints. It calls:

- `POST /volcengine/api/v3/contents/generations/tasks`
- `GET /volcengine/api/v3/contents/generations/tasks/{id}`

## Install

Copy the `seedance-nova` folder into:

```text
~/.codex/skills/
```

Then configure a Nova key either with:

- environment variable `NOVA_LLM_API_KEY`
- or local file `~/.config/seedance-nova/config.json`

Example config:

```json
{
  "base_url": "https://llm-proxy.tapsvc.com",
  "api_key": "replace-with-your-key",
  "default_model": "doubao-seedance-2-0-fast-260128",
  "default_ratio": "16:9",
  "default_resolution": "480p",
  "default_duration": 4,
  "default_generate_audio": false
}
```

## Manual usage

```bash
python3 scripts/seedance.py probe
```

```bash
python3 scripts/seedance.py generate \
  --prompt "A quiet empty street after rain, realistic camera movement, cinematic reflections." \
  --output ./outputs/test.mp4
```

```bash
python3 scripts/seedance.py status TASK_ID
```

## Notes

- Conservative defaults are deliberate: `fast` model, `480p`, `16:9`, `4s`, audio off.
- If a task returns `InternalServiceError`, retry with the defaults before increasing duration or resolution.
