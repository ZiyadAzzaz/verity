> **Superseded by [HANDOVER.md](HANDOVER.md)**, which consolidates everything into one
> document. This file is kept for history only.

# Docker on this machine — root cause and the move to E:\wsl

## The actual root cause: C: was completely full

```
C:  used 197.6 GB   free 0.0 GB      <-- zero bytes
D:  used 151.8 GB   free 55.9 GB
E:  used 714.0 GB   free 217.5 GB
```

A WSL2 VM cannot start its services with no disk space. That is why Docker Desktop's
backend logged, for thirteen minutes straight:

```
apiproxy  << GET /_ping Internal Server Error: context deadline exceeded (15.0s)
GET failed with Get "http://unix/forwards/list": context deadline exceeded
still waiting to toggle VM Otel collector settings in the VM after 13m0.6s
```

The named pipes existed and accepted connections, so `docker info` connected and then waited
forever for a reply that could never come. That is why every call **hung** instead of failing
fast.

### Two earlier diagnoses of mine were wrong

1. **"Docker is stuck on the onboarding/licence screen."** It is not.
   `settings-store.json` has `"DisplayedOnboarding": true` — onboarding was completed long
   ago. I inferred a dialog from "processes running but CLI hangs" instead of reading the
   logs.
2. **"The pip install failed on a corrupted cache."** It did not. The disk was full.
   `--no-cache-dir` appeared to fix it only because it stopped writing 2.6 GB of cache to a
   disk with nothing left. Same root cause as the Docker failure — one fault, two symptoms.

---

## What has been done already

Docker Desktop and WSL were shut down cleanly, both VHDX files confirmed unlocked, and the
Docker data tree was **relocated** (moved, not deleted) with `robocopy /MOVE`:

| | Before | After |
|---|---|---|
| Docker data | `C:\Users\Lenovo\AppData\Local\Docker` | **`E:\wsl\Docker`** |
| `docker_data.vhdx` (images, containers) | C: | **`E:\wsl\Docker\wsl\disk\`** — 1.89 GB |
| `ext4.vhdx` (the VM root) | C: | **`E:\wsl\Docker\wsl\main\`** — 0.09 GB |
| C: free space | **0.00 GB** | **2.40 GB** |

Your only WSL distribution *is* `docker-desktop`, so this moved WSL's data too — one
operation covered both.

**Three zero-byte files could not be moved** and are still at the old path:

```
\run\dockerEthernetVfkit
\run\dockerInference
\run\sailor-ingest.sock
```

These are named pipes and sockets, not data. Windows cannot copy socket files, and Docker
recreates them on every start. Nothing was lost.

---

## Step 1 — Finish the move (needs you: two commands, as Administrator)

I cannot do this part. My tooling blocks removal of anything under `AppData`, which is a
guard I am not going to work around silently — even though only three stale zero-byte
sockets remain there.

Open **PowerShell as Administrator** (right-click Start → *Terminal (Admin)*) and run:

```powershell
cmd /c rmdir /s /q "C:\Users\Lenovo\AppData\Local\Docker"
cmd /c mklink /J "C:\Users\Lenovo\AppData\Local\Docker" "E:\wsl\Docker"
```

**What these do:**

- The first removes the now-empty folder holding the three stale sockets. Every byte of real
  data is already at `E:\wsl\Docker` — verified above at 1.99 GB with both VHDX files
  present.
- The second creates a **directory junction**: the old path becomes a transparent pointer to
  the new one. Docker Desktop, WSL, and every tool keep using
  `C:\Users\Lenovo\AppData\Local\Docker` exactly as before, and Windows silently serves the
  data from E:. Nothing needs reconfiguring, and it survives Docker updates.

Expected output from the second command:

```
Junction created for C:\Users\Lenovo\AppData\Local\Docker <<===>> E:\wsl\Docker
```

If `rmdir` complains the directory is not empty or is in use, reboot and run both commands
again before starting Docker — a reboot always clears stale socket handles.

**Do not start Docker Desktop before running these.** With the old path missing, it would
build a fresh empty VM on C: and orphan the 2 GB now sitting on E:.

---

## Step 2 — Start Docker and verify

1. Launch **Docker Desktop**.
2. Wait for **"Engine running"** (green, bottom-left). Allow up to three minutes — it is
   starting from a spinning disk now.

```powershell
docker info --format "{{.ServerVersion}} {{.OSType}}"
```

Expected — returns in seconds rather than hanging:

```
28.6.0 linux
```

Confirm it is genuinely running from E: — this should report a size, and the file should
grow as you pull images:

```powershell
Get-ChildItem E:\wsl\Docker\wsl\disk\docker_data.vhdx | Select-Object FullName,Length
```

---

## Step 3 — Confirm the whole machine is ready

```powershell
conda activate agent-dev
cd "E:\Azzaz CAI\Researches\verity-hackathon"
python scripts/check_setup.py
```

Target:

```
  [ OK ] Python 3.11.15 in 'agent-dev'
  [ OK ] dependencies and dev tooling installed
  [ OK ] GEMINI_API_KEY is set (53 characters)
  [ OK ] profile: env=local store=sqlite queue=asyncio sandbox=docker model=ai_studio
  [ OK ] Docker daemon 28.6.0
READY - everything the local pipeline needs is in place.
```

Paste that output and say **go**. It never prints your key — only whether one is present and
how long it is.

---

## Things you should know

### E: is a spinning disk

`ST1000LM048` is a 5400rpm SATA laptop drive, not an SSD. Docker image builds, container
starts, and `pip install` inside the sandbox will be **noticeably slower** than they were on
C:. With C: at zero bytes there was no alternative, but it is a real trade-off, and it means
Gate 5 (eight real repositories cloned and installed) will take longer than the 1–3 hours
estimated.

### C: is still nearly full

2.40 GB free on a 197.6 GB system drive is still an unhealthy margin — Windows Update,
hibernation, and temp files all want more than that. Nothing was deleted during this move, so
the space is still consumed by:

| | |
|---|---|
| `AppData\Local` | 43.6 GB |
| `Program Files` | 33.9 GB |
| `Program Files (x86)` | 21.6 GB |
| `ProgramData` | 14.5 GB |
| `Windows\Installer` | 10.9 GB |
| `AppData\Roaming` | 10.8 GB |

Reclaimable without touching anything you use, whenever you want it — say the word and I will
relocate rather than delete:

| Cache | Size | Note |
|---|---|---|
| `AppData\Local\pip\Cache` | 2.62 GB | rebuilt on demand |
| `AppData\Local\Temp` | 2.01 GB | temp files |
| `.cache\codex-runtimes` | 1.08 GB | |
| `.cache\torch` | 0.47 GB | model weights, re-downloadable |
| `.cache\huggingface` | 0.33 GB | model weights, re-downloadable |

### Other things still on C:

The Docker Desktop **application** (3.43 GB at `AppData\Local\Programs\DockerDesktop`) and
`.docker` config (0.66 GB) were left in place. The application is managed by Docker's own
installer and updater; relocating it tends to break updates, and it is not what grows over
time. The VM disk — the part that actually grows with every image you pull — is the one now
on E:.

Say the word if you want `.docker` moved too; that one is safe.
