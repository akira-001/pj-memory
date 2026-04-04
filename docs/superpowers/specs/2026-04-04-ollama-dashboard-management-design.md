# Ollama Dashboard Management — Design Spec

## Overview

cogmem ダッシュボードに Ollama のプロセス管理・モデル管理・自動起動管理機能を追加する。

**目的:** ダッシュボードから Ollama の稼働状態を一目で確認し、必要に応じて起動/停止・モデルpull/削除・macOS ログイン時自動起動の ON/OFF を操作できるようにする。

## Scope

| Feature | Description |
|---------|-------------|
| ステータス表示 | メモリー概要ページの stats-grid に Ollama ステータスカードを追加 |
| プロセス制御 | `ollama serve` の起動/停止/再起動 |
| モデル管理 | cogmem 設定の `embedding_model` の存在確認・pull・削除 |
| 自動起動管理 | macOS LaunchAgent による `ollama serve` のログイン時自動起動 ON/OFF |

## Architecture

### New Files

```
src/cognitive_memory/dashboard/
├── services/ollama_service.py    # Ollama API / process / LaunchAgent operations
├── routes/system.py              # /system routes
└── templates/system/
    └── index.html                # System management page
```

### Modified Files

| File | Change |
|------|--------|
| `app.py` | Register system router (`/system`) |
| `base.html` | Add "System" link to sidebar (bottom, below search) |
| `i18n.py` | Add system-related translation keys |
| `routes/memory.py` | Pass Ollama status to template |
| `templates/memory/overview.html` | Add 5th stat-card for Ollama status |

## Components

### 1. ollama_service.py

All Ollama interactions go through this service. No external dependencies — uses `urllib.request` (matching existing `embeddings/ollama.py` pattern) and `subprocess`.

| Function | Description |
|----------|-------------|
| `get_status() -> str` | `GET /api/tags` with 2s timeout. Returns `"running"` / `"stopped"` |
| `get_models() -> list[dict]` | `GET /api/tags` → list of `{name, size, modified_at}` |
| `check_embedding_model(config) -> dict` | Check if config's `embedding_model` exists. Returns `{status, name, size}` |
| `pull_model(model_name) -> bool` | `POST /api/pull` — blocks until complete (long timeout: 5min) |
| `delete_model(model_name) -> bool` | `DELETE /api/delete` |
| `start_serve() -> bool` | `subprocess.Popen(["ollama", "serve"])` detached, wait 2s, verify status |
| `stop_serve() -> bool` | Find `ollama serve` process via `pgrep`, send SIGTERM |
| `restart_serve() -> bool` | `stop_serve()` then `start_serve()` |
| `is_ollama_installed() -> bool` | `shutil.which("ollama")` |
| `get_launchagent_status() -> dict` | Check `~/Library/LaunchAgents/com.ollama.serve.plist` existence and loaded state |
| `set_launchagent(enabled: bool) -> bool` | Create/remove plist, `launchctl load/unload` |

### 2. Memory Overview — Ollama Stat Card

5th card in existing stats-grid. Three states:

- **Running + model loaded** (green dot): "Running" + model name badge
- **Stopped** (red dot): "Stopped" + "Embedding unavailable"
- **Running + model missing** (yellow dot): "Running" + "Model not found — pull required" with link to `/system`

Data flow: `routes/memory.py` calls `ollama_service.get_status()` and `check_embedding_model(config)`, passes result to template.

### 3. System Page (`/system`)

Three sections using existing card styling:

**Section A: Ollama Process**
- Status indicator (green/red dot + Running/Stopped text)
- Start / Stop / Restart buttons
- Start disabled when running; Stop disabled when stopped
- htmx: `hx-post="/system/ollama/{action}"` → re-renders section

**Section B: Embedding Model**
- Table: model name, size, status (Loaded/Not Found)
- Pull button (shown when model not found)
- Delete button (shown when model exists)
- Pull shows "Pulling..." spinner during download
- htmx: `hx-post="/system/model/pull"`, `hx-delete="/system/model/delete"` → re-renders table

**Section C: Auto-start on Login**
- Toggle switch for LaunchAgent
- Shows plist path: `~/Library/LaunchAgents/com.ollama.serve.plist`
- htmx: `hx-post="/system/launchagent/toggle"` → re-renders toggle

### 4. LaunchAgent plist template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ollama.serve</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/ollama</string>
        <string>serve</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Note: `ollama` binary path resolved via `shutil.which("ollama")` at plist generation time.

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/system` | Render system page |
| POST | `/system/ollama/start` | Start ollama serve |
| POST | `/system/ollama/stop` | Stop ollama serve |
| POST | `/system/ollama/restart` | Restart ollama serve |
| POST | `/system/model/pull` | Pull embedding model |
| DELETE | `/system/model/delete` | Delete embedding model |
| POST | `/system/launchagent/toggle` | Toggle auto-start |

All POST/DELETE routes return HTML fragments for htmx partial updates.

## Error Handling

| Case | Behavior |
|------|----------|
| Ollama not installed | System page shows "Ollama not found" message, all controls disabled |
| Connection timeout (status check) | Treat as `stopped` |
| Pull timeout (5min) | Show error message, allow retry |
| LaunchAgent permission error | Display error message as-is |
| Process kill failure | Display error, suggest manual intervention |

## i18n Keys

New translation keys under `system.*` and `nav.system` namespaces, following existing en/ja pattern in `i18n.py`.

## Sidebar

New entry at bottom of sidebar (below search):

```html
<a href="/system" class="nav-link {% if active_page == 'system' %}active{% endif %}">
    <span class="nav-icon">&#9881;</span> <span class="nav-text">{{ t('nav.system', lang) }}</span>
</a>
```

Icon: gear (&#9881;)
