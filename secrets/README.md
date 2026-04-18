Place secrets for local or VPS Docker runs here.

- `google-drive-service-account.json`
  Google service account JSON used for Google Drive import.

This directory is mounted into the containers as `/run/secrets`.
JSON files in this directory are ignored by Git and excluded from the Docker build context.
