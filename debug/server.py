"""Debug-Webserver: Zeigt alle DB-Tabellen als HTML-Tabellen an."""

import sqlite3
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "bot.db"))
PORT = int(os.getenv("DEBUG_PORT", "8888"))

HTML_HEAD = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>DB Debug</title>
<style>
  body { font-family: monospace; margin: 2em; background: #1a1a1a; color: #e0e0e0; }
  h1 { color: #8f8; }
  h2 { color: #8cf; margin-top: 2em; }
  table { border-collapse: collapse; margin-bottom: 1em; width: 100%; }
  th, td { border: 1px solid #444; padding: 6px 10px; text-align: left; }
  th { background: #333; color: #ff0; }
  tr:nth-child(even) { background: #222; }
  .empty { color: #888; font-style: italic; }
  .count { color: #888; font-size: 0.9em; }
</style>
</head><body>"""

HTML_FOOT = "</body></html>"


def render_table(cursor, table_name):
    rows = cursor.execute(f"SELECT * FROM [{table_name}]").fetchall()
    cols = [desc[0] for desc in cursor.description]
    count = len(rows)

    html = f'<h2>{table_name} <span class="count">({count} rows)</span></h2>'
    if not rows:
        return html + '<p class="empty">Keine Daten.</p>'

    html += "<table><tr>"
    for col in cols:
        html += f"<th>{col}</th>"
    html += "</tr>"
    for row in rows:
        html += "<tr>"
        for val in row:
            display = str(val) if val is not None else '<span class="empty">NULL</span>'
            html += f"<td>{display}</td>"
        html += "</tr>"
    html += "</table>"
    return html


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]

            body = HTML_HEAD + f"<h1>DB Debug — {os.path.basename(DB_PATH)}</h1>"
            for t in tables:
                body += render_table(cur, t)
            body += HTML_FOOT
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())

    def log_message(self, fmt, *args):
        print(f"[debug] {args[0]}")


if __name__ == "__main__":
    print(f"Debug-Server: http://localhost:{PORT}")
    print(f"DB: {DB_PATH}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
