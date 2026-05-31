# SPDX-License-Identifier: MIT
# Licensed under MIT
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--secret", required=True)
    parser.add_argument("--body", required=True)
    args = parser.parse_args()

    timestamp = str(int(time.time()))
    raw = args.body.encode("utf-8")
    payload = timestamp.encode("utf-8") + b"." + raw
    signature = hmac.new(args.secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    print(
        json.dumps(
            {
                "x-qarar-timestamp": timestamp,
                "x-qarar-signature": signature,
                "body": args.body,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
