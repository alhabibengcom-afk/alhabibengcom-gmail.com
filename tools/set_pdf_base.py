"""Change website destinations in the downloadable PDFs after moving the directory."""
import argparse
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pymupdf


def directory_url(value):
    url = urlsplit(value)
    if url.scheme not in {"http", "https"} or not url.netloc or url.query or url.fragment:
        raise argparse.ArgumentTypeError("Enter an HTTP(S) directory URL without a query or fragment.")
    return url._replace(path=url.path.rstrip("/") + "/")


def change_file(path, old, new):
    changes = 0
    temporary = path.with_suffix(".updated.pdf")
    with pymupdf.open(path) as document:
        for page in document:
            for link in page.get_links():
                if link["kind"] != pymupdf.LINK_URI:
                    continue
                url = urlsplit(link["uri"])
                if (url.scheme, url.netloc, url.path.rstrip("/")) != (
                    old.scheme, old.netloc, old.path.rstrip("/")
                ):
                    continue
                replacement = urlunsplit(new._replace(query=url.query, fragment=url.fragment))
                if replacement != link["uri"]:
                    link["uri"] = replacement
                    page.update_link(link)
                    changes += 1
        if changes:
            document.save(temporary, garbage=3, deflate=True)
    if changes:
        temporary.replace(path)
    return changes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_url", type=directory_url)
    parser.add_argument("new_url", type=directory_url)
    parser.add_argument("--site-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "brands")
    args = parser.parse_args()
    if not (args.site_dir / "index.html").is_file():
        parser.error("The site directory must contain index.html")
    for pdf_path in sorted(args.site_dir.rglob("*.pdf")):
        count = change_file(pdf_path, args.old_url, args.new_url)
        print(f"{pdf_path.relative_to(args.site_dir)}: {count} updated")
