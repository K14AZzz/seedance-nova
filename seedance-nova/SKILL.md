---
name: seedance-nova
description: Use when the user wants to generate Seedance 2.0 videos through Nova AI Gateway at llm-proxy.tapsvc.com, check task status, or download finished videos. This skill uses the Volcengine passthrough endpoints instead of fal or OpenAI video endpoints.
---

# Seedance Nova

Use this skill for Seedance 2.0 work on Nova AI Gateway.

Primary script:
- `scripts/seedance.py`

Workflow:
1. Run `probe` to confirm the gateway and visible Seedance models.
2. For a new video, prefer conservative defaults first:
   - model `doubao-seedance-2-0-fast-260128`
   - `480p`
   - `16:9`
   - `4s`
   - audio off
3. If the user only wants a task id, use `submit`.
4. Use `status` to poll an existing task.
5. Use `download` only after `status` is `succeeded`.

Examples:
- `python3 scripts/seedance.py probe`
- `python3 scripts/seedance.py generate --prompt "A quiet empty street after rain, realistic camera movement, cinematic reflections." --output ./outputs/seedance.mp4`
- `python3 scripts/seedance.py status cgt-xxxx`

Read `references/config.example.json` when you need the expected local config shape.

Notes:
- The correct API path is `/volcengine/api/v3/contents/generations/tasks`.
- Do not route Nova Seedance calls through `fal` or `/v1/videos`.
- If a task fails with `InternalServiceError`, retry with the conservative defaults before changing models.
