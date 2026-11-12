# Phase 13 — API Coverage Decision

The api-coverage detector fired on the phrase "grows the FileWatcher scheduling lifecycle API that Phase 14+ hosts also consume" (13-CONTEXT D-15) — internal Python API prose, not an external API/SDK/service integration. The only external surfaces Phase 13 touches are the OS service managers (launchctl / systemctl), invoked as local binaries via explicit argv subprocess calls, plus generated text files (launchd plist / systemd unit). Per the checkpoint rule those manager invocations are enumerated below as the capability surface, each with an explicit decision — nothing is left implicit.

| capability | decision | reason |
|---|---|---|
| `launchctl bootstrap gui/$(id -u) <plist>` | INTEGRATE | service install path (D-12) |
| `launchctl bootout gui/$(id -u)/com.docsif.watch` | INTEGRATE | uninstall + re-install conflict handling (D-12, Pitfall 5) |
| `launchctl print gui/$(id -u)/com.docsif.watch` | INTEGRATE | post-install verification (D-12) |
| `systemctl --user daemon-reload` | INTEGRATE | Linux install prerequisite (D-12/D-13) |
| `systemctl --user enable --now sif-watch` | INTEGRATE | Linux install + start (D-12/D-13) |
| `systemctl --user is-active sif-watch` | INTEGRATE | post-install verification (D-12) |
| `systemctl --user disable --now sif-watch` | INTEGRATE | Linux uninstall (stop-then-remove semantics) |
| `loginctl enable-linger $USER` | OPT-OUT | survive-logout is documented in install output (D-13) but not invoked by sif — a deliberate one-time user action |
| `launchctl kickstart` | OPT-OUT | re-install refresh handled by bootout-then-bootstrap; kickstart not required |
| `launchctl list` / other manager read commands | OPT-OUT | status visibility comes from the PID file + `sif status` (D-08), not manager polling |

All invocations use explicit argv lists via `subprocess.run` — never `shell=True` (D-12, threat T-13-10).
