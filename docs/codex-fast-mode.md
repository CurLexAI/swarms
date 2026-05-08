# Codex Fast Mode and Codex-Spark

## Fast mode

Fast mode increases supported model throughput by ~1.5x in Codex surfaces that support tiered credits.

- Toggle commands in Codex CLI:
  - `/fast on`
  - `/fast off`
  - `/fast status`
- Persistent configuration in `config.toml`:

```toml
service_tier = "fast"

[features]
fast_mode = true
```

### Credit consumption

- GPT-5.5 in fast mode consumes credits at 2.5x the Standard rate.
- GPT-5.4 in fast mode consumes credits at 2x the Standard rate.

### Availability

Fast mode is available in:

- Codex IDE extension
- Codex CLI
- Codex app when authenticated with ChatGPT

When authenticated with an API key, Codex uses standard API pricing and fast-mode credits do not apply.

## Codex-Spark

GPT-5.3-Codex-Spark is a separate, lower-latency and lower-capability Codex model optimized for near-instant iteration. It is distinct from fast mode (which accelerates another selected model and changes credit burn).

During research preview, Codex-Spark availability is limited to ChatGPT Pro subscribers.
