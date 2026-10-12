"""Maakt de downloadbare PDF's van de privacyverklaringen.
Gebruik (vanuit de repo-map):  python3 tools/make-privacy-pdfs.py
Resultaat: site/downloads/*.pdf  (draai opnieuw na elke tekstwijziging)."""
import http.server, threading, functools, pathlib, subprocess
from playwright.sync_api import sync_playwright

SITE = pathlib.Path(__file__).resolve().parent.parent / "site"
OUT = SITE / "downloads"
LANGS = ["nl", "en", "de", "fr", "es", "it"]
# (pagina, PDF-naam): elke pagina heeft alle 6 talen; per taal een eigen PDF
PAGES = [("privacy.html", "mariodigital-privacy"), ("bypeek/privacy/", "bypeek-privacy"),
         ("pinline/privacy/", "pinline-privacy")]
JOBS = [(path, l, f"{name}-{l}.pdf") for path, name in PAGES for l in LANGS]

# Links in de PDF moeten naar de echte site wijzen, niet naar localhost.
FIX_LINKS = """() => { for (const a of document.querySelectorAll('a[href]')) {
  const u = new URL(a.href, location.href);
  if (u.hostname === location.hostname) a.href = 'https://mariodigital.eu' + u.pathname + u.hash; } }"""

def main():
    OUT.mkdir(exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    handler.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(color_scheme="light")
        for path, keep, name in JOBS:
            page.goto("about:blank")  # verse pagina, anders stapelen de verberg-stijlen op
            page.goto(base + path + "#" + keep, wait_until="networkidle")
            # alle talen staan op één pagina: toon alleen de gekozen taal
            page.add_style_tag(content=f"main > section:not(#{keep}){{display:none!important}}")
            page.evaluate(FIX_LINKS)
            page.emulate_media(media="print")
            page.pdf(path=str(OUT / name), format="A4", print_background=True,
                     margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"})
            # controle: een PDF zonder tekst betekent dat de verkeerde taal verborgen is
            words = len(subprocess.run(["pdftotext", str(OUT / name), "-"], capture_output=True, text=True).stdout.split())
            if words < 100:
                raise SystemExit(f"FOUT: {name} bevat maar {words} woorden")
            print("gemaakt:", name, f"({words} woorden)")
        b.close()
    srv.shutdown()

if __name__ == "__main__":
    main()
