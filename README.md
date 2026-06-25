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

## Install for Codex

This repository is meant to be copied into a Codex skill directory.

### 1. Copy the skill into Codex

Copy the `seedance-nova` folder into:

```text
~/.codex/skills/
```

After copying, the expected layout is:

```text
~/.codex/skills/
└── seedance-nova/
    ├── SKILL.md
    ├── scripts/
    │   └── seedance.py
    └── references/
        └── config.example.json
```

### 2. Provide a Nova API key

Each user should normally use their **own** Nova key.

You can configure the key in either of these ways:

- environment variable `NOVA_LLM_API_KEY`
- local file `~/.config/seedance-nova/config.json`

### 3. Create local config (optional but recommended)

Create:

```text
~/.config/seedance-nova/config.json
```

Example:

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

You can also start from:

```text
seedance-nova/references/config.example.json
```

### 4. Verify the installation

Run:

```bash
python3 ~/.codex/skills/seedance-nova/scripts/seedance.py probe
```

If setup is correct, you should see visible Seedance model ids from Nova.

### 5. Use it from Codex

Once the folder is under `~/.codex/skills/`, other Codex sessions on the same machine should be able to discover it automatically.

Typical prompts:

- `用 seedance-nova 生成一个 4 秒 16:9 的雨夜街景视频`
- `帮我检查 seedance-nova 现在能看到哪些模型`
- `用 seedance-nova 查询这个任务状态：cgt-xxxx`

## Manual CLI usage

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

## Commands

- `probe`: check gateway connectivity and visible Seedance models
- `submit`: create a task and return its task id
- `status`: query an existing task
- `download`: download a finished video from a successful task
- `generate`: create a task, poll until finished, and optionally download the output

## Security notes

- Do not commit real API keys into this repository.
- Prefer per-user keys for auditability, quota control, and safer revocation.
- If multiple people share one key, they also share spend, rate limits, and operational risk.

## Notes

- Conservative defaults are deliberate: `fast` model, `480p`, `16:9`, `4s`, audio off.
- If a task returns `InternalServiceError`, retry with the defaults before increasing duration or resolution.
