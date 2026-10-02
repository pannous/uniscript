"""A static server with HTTP Range support (multi-range as multipart/byteranges), like Apache for chunks.pack.
Usage: python3 probes/chinese/range_server.py PORT   (serves the current directory)"""
import http.server
import os
import re
import sys

BOUNDARY = "uniscript-ranges"


class RangeHandler(http.server.SimpleHTTPRequestHandler):
	def send_head(self):
		ranges = re.findall(r"(\d+)-(\d+)", self.headers.get("Range", ""))
		path = self.translate_path(self.path)
		if not ranges or not os.path.isfile(path):
			return super().send_head()
		data = open(path, "rb").read()
		parts = [(int(start), min(int(end), len(data) - 1)) for start, end in ranges]
		self.send_response(206)
		if len(parts) == 1:
			start, end = parts[0]
			body = data[start:end + 1]
			self.send_header("Content-Type", "application/octet-stream")
			self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
		else:
			body = b"".join(f"--{BOUNDARY}\r\nContent-Type: application/octet-stream\r\nContent-Range: bytes {s}-{e}/{len(data)}\r\n\r\n".encode() + data[s:e + 1] + b"\r\n" for s, e in parts) + f"--{BOUNDARY}--\r\n".encode()
			self.send_header("Content-Type", f"multipart/byteranges; boundary={BOUNDARY}")
		self.send_header("Content-Length", str(len(body)))
		self.end_headers()
		self.wfile.write(body)
		return None


http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), RangeHandler).serve_forever()
