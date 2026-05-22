---
name: hf-cli
description: "operate the hugging face hub cli (`hf`) for downloading, uploading, and managing repositories, models, datasets, and spaces on the hugging face hub. use when pulling model weights, uploading artifacts, managing hf repos/datasets/spaces, running hf jobs, querying dataset sql, or verifying hf auth. the `hf` command replaces the deprecated `huggingface-cli`."
---

# Hugging Face Hub CLI

## Install

```bash
curl -LsSf https://hf.co/cli/install.sh | bash -s
```

Verify: `hf version`

## Authentication

```bash
hf auth whoami        # check current login
hf auth login         # interactive login (token from huggingface.co/settings/tokens)
hf auth list          # list stored tokens
hf auth switch        # switch between tokens
hf auth logout        # remove a stored token
```

Prefer the `HF_TOKEN` env var for CI and non-interactive use. Never commit tokens.

Report only:

```text
HF_TOKEN=SET|UNSET
```

## Core commands

| Command | Purpose |
|---|---|
| `hf download REPO_ID` | Download files from the Hub |
| `hf upload REPO_ID` | Upload file or folder (single-commit) |
| `hf upload-large-folder REPO_ID LOCAL_PATH` | Resumable upload for large folders |
| `hf sync` | Sync files between local directory and a bucket |
| `hf env` | Print environment info |
| `hf version` | Print CLI version |

## Repository management (`hf repos`)

| Command | Purpose |
|---|---|
| `hf repos create REPO_ID` | Create a new repo |
| `hf repos delete REPO_ID` | Delete a repo (irreversible) |
| `hf repos delete-files REPO_ID PATTERNS` | Delete files from a repo |
| `hf repos duplicate FROM_ID` | Duplicate a repo |
| `hf repos move FROM_ID TO_ID` | Move repo between namespaces |
| `hf repos settings REPO_ID` | Update repo settings |
| `hf repos branch` | Manage branches |
| `hf repos tag` | Manage tags |

## Models and datasets

```bash
hf models ls                        # list models
hf models info MODEL_ID             # model details
hf datasets ls                      # list datasets
hf datasets info DATASET_ID         # dataset details
hf datasets parquet DATASET_ID      # list parquet URLs
hf datasets sql SQL                 # run SQL via DuckDB against parquet
```

## Spaces

```bash
hf spaces ls                        # list spaces
hf spaces info SPACE_ID             # space details
hf spaces dev-mode SPACE_ID         # toggle dev mode
hf spaces hot-reload SPACE_ID       # hot-reload Python files
```

## Jobs (`hf jobs`)

```bash
hf jobs run IMAGE COMMAND           # run a job
hf jobs uv                          # run UV scripts on HF infrastructure
hf jobs ps                          # list jobs
hf jobs inspect JOB_IDS             # job details
hf jobs logs JOB_ID                 # fetch logs
hf jobs cancel JOB_ID               # cancel a job
hf jobs stats                       # resource usage statistics
hf jobs hardware                    # list available hardware
hf jobs scheduled                   # manage scheduled jobs
```

## Cache management (`hf cache`)

```bash
hf cache ls                         # list cached repos/revisions
hf cache prune                      # remove detached revisions
hf cache rm TARGETS                 # remove specific cached items
hf cache verify REPO_ID             # verify checksums
```

## Buckets (`hf buckets`)

```bash
hf buckets create BUCKET_ID
hf buckets delete BUCKET_ID
hf buckets info BUCKET_ID
hf buckets list
hf buckets cp SRC                   # copy single file to/from bucket
hf buckets sync                     # sync local dir <-> bucket
hf buckets move FROM_ID TO_ID       # rename bucket
hf buckets remove ARGUMENT          # remove files from bucket
```

## Collections (`hf collections`)

```bash
hf collections create TITLE
hf collections ls
hf collections info COLLECTION_SLUG
hf collections delete COLLECTION_SLUG
hf collections update COLLECTION_SLUG
hf collections add-item COLLECTION_SLUG ITEM_ID ITEM_TYPE
hf collections delete-item COLLECTION_SLUG ITEM_OBJECT_ID
hf collections update-item COLLECTION_SLUG ITEM_OBJECT_ID
```

## Discussions and pull requests (`hf discussions`)

```bash
hf discussions list REPO_ID
hf discussions info REPO_ID NUM
hf discussions create REPO_ID title
hf discussions comment REPO_ID NUM
hf discussions diff REPO_ID NUM     # show PR diff
hf discussions merge REPO_ID NUM
hf discussions close REPO_ID NUM
hf discussions reopen REPO_ID NUM
hf discussions rename REPO_ID NUM NEW_TITLE
```

## Inference Endpoints (`hf endpoints`)

```bash
hf endpoints ls
hf endpoints describe NAME
hf endpoints deploy NAME repo framework accelerator instance_size instance_type region vendor
hf endpoints update NAME
hf endpoints pause NAME
hf endpoints resume NAME
hf endpoints scale-to-zero NAME
hf endpoints delete NAME
hf endpoints catalog
```

## Webhooks (`hf webhooks`)

```bash
hf webhooks list
hf webhooks info WEBHOOK_ID
hf webhooks create watch
hf webhooks update WEBHOOK_ID
hf webhooks enable WEBHOOK_ID
hf webhooks disable WEBHOOK_ID
hf webhooks delete WEBHOOK_ID
```

## Extensions (`hf extensions`)

```bash
hf extensions list
hf extensions install REPO_ID
hf extensions exec NAME
hf extensions remove NAME
```

## Papers (`hf papers`)

```bash
hf papers ls                        # list daily papers
```

## Tips

- Use `hf <command> --help` for full options and examples.
- Use `--format json` for machine-readable output on list commands.
- Use `-q` / `--quiet` to print only IDs.
- Authenticate with `HF_TOKEN` env var (recommended) or `--token`.

## Hard rules

- Never commit HF tokens, API keys, or `.env` files.
- Never print token values; report only `SET`/`UNSET`.
- Modal pulls from Hugging Face are backend-only; never expose HF download URLs to public/client surfaces.
- Verify `hf auth whoami` before claiming authenticated access.

## Verdicts

- READY: `hf` installed, authenticated, target repo accessible.
- HOLD: `hf` installed but auth or network not verified.
- BLOCK: missing `hf` binary or critical auth failure.
- UNVERIFIED: cannot inspect HF CLI state.
