import os

files = ['scripts/start-api.sh', 'scripts/start-worker.sh']
for f in files:
    if os.path.exists(f):
        with open(f, 'rb') as fh:
            content = fh.read()
        # Convert CRLF to LF
        new_content = content.replace(b'\r\n', b'\n')
        with open(f, 'wb') as fh:
            fh.write(new_content)
        print(f"Fixed {f}")
    else:
        print(f"File not found: {f}")
