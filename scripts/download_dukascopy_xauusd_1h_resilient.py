"""Resilient year-wise 1H XAU/USD downloader for TheoryCraft Dukascopy CLI.

Purpose
-------
Download native Dukascopy XAU/USD 1-hour bars from 2003..2026 without hammering
Dukascopy's servers. The script downloads in small calendar chunks, stores chunk
CSVs under each year, combines chunks into one CSV per year, then combines all
available years into a single all-years CSV.

Why this exists
---------------
HTTP 503 from Dukascopy is usually server-side throttling/temporary availability.
The TheoryCraft CLI defaults to parallel batch requests. This wrapper forces a
slow path by default:

    --chunk-months 1 --batch-size 1 --batch-pause 4000 --retry-pause 5000

Directory layout
----------------
<output-dir>/raw/dukascopy/XAUUSD/1H/
    2003/
        chunks/xauusd_h1_2003_01.csv
        chunks/xauusd_h1_2003_02.csv
        ...
        xauusd_h1_2003.csv
    2004/
        ...
    xauusd_h1_2003_2026.csv
<output-dir>/manifests/
    dukascopy_xauusd_1h_manifest.csv
    dukascopy_xauusd_1h_checksums.csv
<output-dir>/logs/
    download_dukascopy_xauusd_1h_resilient.log

Recommended Windows command
---------------------------
python scripts/download_dukascopy_xauusd_1h_resilient.py ^
  --start-year 2003 --end-year 2026 ^
  --output-dir "C:/Users/Abhishek Sharma/Desktop/RawPPO/data" ^
  --chunk-months 1 --batch-size 1 --batch-pause 4000 ^
  --retry-pause 5000 --cli-retries 5 --attempts 6 --timeout 900

If the CLI is not on PATH, pass the escript explicitly, for example:
  --dukascopy-bin "%USERPROFILE%/.mix/escripts/dukascopy.bat"

Notes
-----
* Raw chunk CSVs are left unchanged after successful download.
* Combined year/all-years CSVs are derived artifacts: header-normalized,
  timestamp-sorted, and de-duplicated by the full row.
* Existing non-empty year CSVs are skipped unless --force is supplied.
* If a year fails, its completed chunk CSVs remain for resume, but the final
  year CSV is not overwritten.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import logging
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

INSTRUMENT = "XAU/USD"
TIMEFRAME = "h1"
SYMBOL_DIR = "XAUUSD"
SUBPATH = ("raw", "dukascopy", SYMBOL_DIR, "1H")
log = logging.getLogger("dukascopy_resilient")


@dataclass(frozen=True)
class Chunk:
    year: int
    chunk_id: str
    start: date
    end_exclusive: date | None  # None means pass --to now

    @property
    def filename_stem(self) -> str:
        return f"xauusd_h1_{self.year}_{self.chunk_id}"

    @property
    def to_arg(self) -> str:
        return "now" if self.end_exclusive is None else self.end_exclusive.isoformat()


def find_dukascopy(override: str | None) -> str:
    """Locate the Dukascopy escript. Override > PATH > common Mix escript paths."""
    if override:
        return override

    for name in ("dukascopy", "dukascopy.bat", "dukascopy.cmd"):
        found = shutil.which(name)
        if found:
            return found

    candidates = [
        Path.home() / ".mix" / "escripts" / "dukascopy",
        Path.home() / ".mix" / "escripts" / "dukascopy.bat",
        Path.home() / ".mix" / "escripts" / "dukascopy.cmd",
    ]
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        candidates.extend([
            Path(localappdata) / "Mix" / "escripts" / "dukascopy",
            Path(localappdata) / "Mix" / "escripts" / "dukascopy.bat",
            Path(localappdata) / "Mix" / "escripts" / "dukascopy.cmd",
        ])

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        "dukascopy escript not found on PATH or common Mix escript folders. "
        "Pass --dukascopy-bin, e.g. %USERPROFILE%/.mix/escripts/dukascopy.bat"
    )


def year_range(start: int, end: int, today: date) -> list[int]:
    """Years to attempt: [start..end], dropping years strictly in the future."""
    return [y for y in range(start, end + 1) if y <= today.year]


def add_months(d: date, months: int) -> date:
    """Return the first day after adding N calendar months to a first-of-month date."""
    month_index = (d.year * 12 + d.month - 1) + months
    return date(month_index // 12, month_index % 12 + 1, 1)


def iter_year_chunks(year: int, chunk_months: int, today: date) -> list[Chunk]:
    """Build half-open date chunks for a year.

    For past chunks, --to is the first date after the chunk. If the CLI treats
    --to as exclusive, no end-of-month data is lost. If it treats --to as
    inclusive, duplicate boundary rows are removed when combining.
    """
    if chunk_months < 1 or chunk_months > 12:
        raise ValueError("--chunk-months must be between 1 and 12")

    chunks: list[Chunk] = []
    start = date(year, 1, 1)
    last_possible = today if year == today.year else date(year, 12, 31)
    if start > last_possible:
        return []

    current = start
    while current <= last_possible:
        next_start = add_months(current, chunk_months)
        end_exclusive = next_start
        if year == today.year and end_exclusive > today:
            # Ask the CLI for up-to-now data for the current open chunk.
            chunk_end = None
        else:
            chunk_end = end_exclusive
        # Stable id: MM for monthly, MM-MM for multi-month chunks.
        end_month = min(add_months(current, chunk_months) - timedelta(days=1), last_possible)
        chunk_id = f"{current.month:02d}" if current.month == end_month.month else f"{current.month:02d}-{end_month.month:02d}"
        chunks.append(Chunk(year=year, chunk_id=chunk_id, start=current, end_exclusive=chunk_end))
        current = next_start
    return chunks


def build_cmd(
    binary: str,
    chunk: Chunk,
    tmp_dir: Path,
    price_type: str,
    volume_units: str,
    cli_retries: int,
    retry_pause: int,
    batch_size: int,
    batch_pause: int,
    cache: bool,
    cache_path: Path,
    flats: bool,
) -> list[str]:
    cmd = [
        binary,
        "download",
        "-i", INSTRUMENT,
        "-t", TIMEFRAME,
        "--from", chunk.start.isoformat(),
        "--to", chunk.to_arg,
        "-p", price_type,
        "-v", volume_units,
        "-f", "csv",
        "-o", str(tmp_dir),
        "--filename", chunk.filename_stem,
        "--batch-size", str(batch_size),
        "--batch-pause", str(batch_pause),
        "--retries", str(cli_retries),
        "--retry-pause", str(retry_pause),
        "-s",
    ]
    if cache:
        cmd.extend(["--cache", "--cache-path", str(cache_path)])
    if flats:
        cmd.append("--flats")
    return cmd


def row_looks_like_data(row: list[str]) -> bool:
    if not row:
        return False
    first = row[0].strip().strip('"')
    if not first:
        return False
    if first[0].isdigit():
        return True
    # Allow numeric epoch-like timestamps as well.
    try:
        float(first)
        return True
    except ValueError:
        return False


def row_year(row: list[str]) -> int | None:
    if not row:
        return None
    first = row[0].strip().strip('"')
    if len(first) >= 4 and first[:4].isdigit():
        return int(first[:4])
    return None


def read_csv_rows(path: Path, keep_year: int | None = None) -> tuple[list[str] | None, list[list[str]]]:
    """Return optional header and data rows. Filter rows to keep_year when provided."""
    header: list[str] | None = None
    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if not row:
                continue
            if idx == 0 and not row_looks_like_data(row):
                header = row
                continue
            if keep_year is not None:
                yr = row_year(row)
                # If the timestamp year is parseable, keep only the target year.
                if yr is not None and yr != keep_year:
                    continue
            rows.append(row)
    return header, rows


def combine_csvs(inputs: list[Path], output: Path, keep_year: int | None = None) -> dict:
    """Combine CSVs into one sorted, de-duplicated derived CSV."""
    output.parent.mkdir(parents=True, exist_ok=True)
    header: list[str] | None = None
    seen: set[tuple[str, ...]] = set()
    rows: list[list[str]] = []

    for path in inputs:
        h, data_rows = read_csv_rows(path, keep_year=keep_year)
        if header is None and h:
            header = h
        for row in data_rows:
            key = tuple(row)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

    rows.sort(key=lambda r: r[0] if r else "")
    tmp = output.with_suffix(output.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if header:
            writer.writerow(header)
        writer.writerows(rows)
    tmp.replace(output)
    return file_stats(output)


def file_stats(path: Path) -> dict:
    """sha256 + size + row count + first/last timestamp."""
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            size += len(chunk)

    first_ts = last_ts = ""
    rows = 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if not row:
                continue
            if idx == 0 and not row_looks_like_data(row):
                continue
            rows += 1
            if not first_ts:
                first_ts = row[0]
            last_ts = row[0]

    return {
        "bytes": size,
        "sha256": h.hexdigest(),
        "rows": rows,
        "first_ts": first_ts,
        "last_ts": last_ts,
    }


def run_subprocess_with_retries(cmd: list[str], timeout: int, attempts: int, base_sleep: int, year: int, chunk_id: str) -> bool:
    """Wrapper-level retry with exponential backoff for 503/timeouts."""
    for attempt in range(1, max(1, attempts) + 1):
        log.info("year %s chunk %s: attempt %d/%d", year, chunk_id, attempt, attempts)
        log.debug("command: %s", " ".join(cmd))
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            log.warning("year %s chunk %s: TIMEOUT after %ss", year, chunk_id, timeout)
            proc = None

        if proc is not None and proc.returncode == 0:
            return True

        message = ""
        if proc is not None:
            message = (proc.stderr or proc.stdout or "").strip()
            log.warning("year %s chunk %s: exit %s: %s", year, chunk_id, proc.returncode, message[:800])

        if attempt < attempts:
            # Extra delay is essential for HTTP 503 / server-side throttling.
            sleep_for = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 2.0)
            if "503" in message:
                sleep_for = max(sleep_for, 30.0)
            log.info("year %s chunk %s: sleeping %.1fs before retry", year, chunk_id, sleep_for)
            time.sleep(sleep_for)
    return False


def download_chunk(
    binary: str,
    chunk: Chunk,
    year_dir: Path,
    args: argparse.Namespace,
) -> Path | None:
    chunks_dir = year_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    final_chunk = chunks_dir / f"{chunk.filename_stem}.csv"

    if final_chunk.exists() and final_chunk.stat().st_size > 0 and not args.force:
        log.info("year %s chunk %s: SKIP chunk exists", chunk.year, chunk.chunk_id)
        return final_chunk

    tmp_dir = year_dir / f".tmp_{chunk.filename_stem}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    cmd = build_cmd(
        binary=binary,
        chunk=chunk,
        tmp_dir=tmp_dir,
        price_type=args.price_type,
        volume_units=args.volume_units,
        cli_retries=args.cli_retries,
        retry_pause=args.retry_pause,
        batch_size=args.batch_size,
        batch_pause=args.batch_pause,
        cache=args.cache,
        cache_path=Path(args.output_dir).expanduser().resolve() / ".dukascopy-cache",
        flats=args.flats,
    )

    ok = run_subprocess_with_retries(
        cmd=cmd,
        timeout=args.timeout,
        attempts=args.attempts,
        base_sleep=args.wrapper_pause,
        year=chunk.year,
        chunk_id=chunk.chunk_id,
    )
    if not ok:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    produced = tmp_dir / f"{chunk.filename_stem}.csv"
    if not produced.exists() or produced.stat().st_size == 0:
        log.warning("year %s chunk %s: command succeeded but CSV missing/empty", chunk.year, chunk.chunk_id)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    final_chunk.parent.mkdir(parents=True, exist_ok=True)
    if final_chunk.exists():
        final_chunk.unlink()
    shutil.move(str(produced), str(final_chunk))
    shutil.rmtree(tmp_dir, ignore_errors=True)

    st = file_stats(final_chunk)
    log.info(
        "year %s chunk %s: OK rows=%s bytes=%s first=%s last=%s",
        chunk.year,
        chunk.chunk_id,
        st["rows"],
        st["bytes"],
        st["first_ts"],
        st["last_ts"],
    )
    return final_chunk


def download_year(binary: str, year: int, base: Path, args: argparse.Namespace, today: date) -> dict:
    """Download one year as small chunks, then combine into a clean year CSV."""
    year_dir = base.joinpath(*SUBPATH, str(year))
    final_csv = year_dir / f"xauusd_h1_{year}.csv"
    rec = {
        "year": year,
        "instrument": INSTRUMENT,
        "timeframe": TIMEFRAME,
        "path": str(final_csv),
        "status": "",
        "rows": "",
        "bytes": "",
        "sha256": "",
        "first_ts": "",
        "last_ts": "",
        "chunks": "",
    }

    if final_csv.exists() and final_csv.stat().st_size > 0 and not args.force:
        st = file_stats(final_csv)
        rec.update(status="SKIP_EXISTS", chunks="existing", **st)
        log.info("year %s: SKIP year exists rows=%s bytes=%s", year, st["rows"], st["bytes"])
        return rec

    if args.force and year_dir.exists():
        # Remove old chunk artifacts only for this target year.
        chunks_dir = year_dir / "chunks"
        if chunks_dir.exists():
            shutil.rmtree(chunks_dir, ignore_errors=True)

    year_dir.mkdir(parents=True, exist_ok=True)
    chunks = iter_year_chunks(year, args.chunk_months, today)
    if not chunks:
        rec["status"] = "NO_CHUNKS"
        return rec

    chunk_paths: list[Path] = []
    failed: list[str] = []
    for chunk in chunks:
        path = download_chunk(binary, chunk, year_dir, args)
        if path is None:
            failed.append(chunk.chunk_id)
            if not args.continue_year_on_chunk_error:
                break
        else:
            chunk_paths.append(path)

    if failed:
        rec.update(status="FAILED", chunks=f"failed:{','.join(failed)}")
        log.error("year %s: FAILED chunks=%s; final year CSV left untouched", year, failed)
        return rec

    if not chunk_paths:
        rec.update(status="FAILED", chunks="no successful chunks")
        return rec

    st = combine_csvs(chunk_paths, final_csv, keep_year=year)
    if st["rows"] == 0 and not args.allow_empty_year:
        final_csv.unlink(missing_ok=True)
        rec.update(status="FAILED_EMPTY", chunks=str(len(chunk_paths)))
        log.error("year %s: combined CSV has zero rows; use --allow-empty-year only if this is expected", year)
        return rec

    rec.update(status="OK", chunks=str(len(chunk_paths)), **st)
    log.info(
        "year %s: OK combined rows=%s bytes=%s first=%s last=%s",
        year,
        st["rows"],
        st["bytes"],
        st["first_ts"],
        st["last_ts"],
    )
    return rec


def combine_all_years(records: list[dict], base: Path, start_year: int, end_year: int) -> Path | None:
    ok_paths = [Path(r["path"]) for r in records if r.get("status") in {"OK", "SKIP_EXISTS"} and Path(r["path"]).exists()]
    if not ok_paths:
        log.warning("combined all-years CSV not written: no successful year CSVs")
        return None
    combined = base.joinpath(*SUBPATH, f"xauusd_h1_{start_year}_{end_year}.csv")
    st = combine_csvs(ok_paths, combined, keep_year=None)
    log.info("combined all-years -> %s rows=%s first=%s last=%s", combined, st["rows"], st["first_ts"], st["last_ts"])
    return combined


def write_manifest(records: list[dict], manifest_dir: Path, combined_path: Path | None) -> None:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    man = manifest_dir / "dukascopy_xauusd_1h_manifest.csv"
    chk = manifest_dir / "dukascopy_xauusd_1h_checksums.csv"
    cols = [
        "year", "instrument", "timeframe", "path", "status", "chunks", "rows",
        "bytes", "first_ts", "last_ts", "sha256",
    ]
    with man.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in cols})
        if combined_path and combined_path.exists():
            st = file_stats(combined_path)
            writer.writerow({
                "year": "ALL",
                "instrument": INSTRUMENT,
                "timeframe": TIMEFRAME,
                "path": str(combined_path),
                "status": "COMBINED",
                "chunks": "",
                **st,
            })

    with chk.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "sha256", "bytes"])
        for rec in records:
            if rec.get("sha256"):
                writer.writerow([rec["path"], rec["sha256"], rec["bytes"]])
        if combined_path and combined_path.exists():
            st = file_stats(combined_path)
            writer.writerow([str(combined_path), st["sha256"], st["bytes"]])

    log.info("manifest -> %s", man)
    log.info("checksums -> %s", chk)


def run(args: argparse.Namespace) -> int:
    today = date.today()
    base = Path(args.output_dir).expanduser().resolve()
    years = year_range(args.start_year, args.end_year, today)
    if not years:
        log.error("no valid years in range %s..%s", args.start_year, args.end_year)
        return 2

    if args.dry_run:
        binary = args.dukascopy_bin or "dukascopy"
        print(f"# DRY RUN - base: {base}")
        print(f"# slow mode: chunk_months={args.chunk_months}, batch_size={args.batch_size}, batch_pause={args.batch_pause}ms")
        for year in years:
            year_dir = base.joinpath(*SUBPATH, str(year))
            for chunk in iter_year_chunks(year, args.chunk_months, today):
                tmp = year_dir / f".tmp_{chunk.filename_stem}"
                cmd = build_cmd(
                    binary=binary,
                    chunk=chunk,
                    tmp_dir=tmp,
                    price_type=args.price_type,
                    volume_units=args.volume_units,
                    cli_retries=args.cli_retries,
                    retry_pause=args.retry_pause,
                    batch_size=args.batch_size,
                    batch_pause=args.batch_pause,
                    cache=args.cache,
                    cache_path=base / ".dukascopy-cache",
                    flats=args.flats,
                )
                print("  " + " ".join(cmd))
        print(f"# {len(years)} year(s); final combined CSV -> {base.joinpath(*SUBPATH, f'xauusd_h1_{years[0]}_{years[-1]}.csv')}")
        return 0

    binary = find_dukascopy(args.dukascopy_bin)
    log.info("dukascopy: %s | instrument=%s | timeframe=%s | years=%s..%s", binary, INSTRUMENT, TIMEFRAME, years[0], years[-1])
    log.info("output: %s", base)
    log.info("503-safe settings: chunk_months=%s batch_size=%s batch_pause=%sms cli_retries=%s retry_pause=%sms attempts=%s wrapper_pause=%ss", args.chunk_months, args.batch_size, args.batch_pause, args.cli_retries, args.retry_pause, args.attempts, args.wrapper_pause)

    records = [download_year(binary, year, base, args, today) for year in years]
    combined_path = combine_all_years(records, base, years[0], years[-1])
    write_manifest(records, base / "manifests", combined_path)

    ok = sum(rec["status"] in {"OK", "SKIP_EXISTS"} for rec in records)
    failed = [rec["year"] for rec in records if rec["status"] not in {"OK", "SKIP_EXISTS"}]
    log.info("done: %d/%d years present; failed=%s", ok, len(records), failed or "none")
    return 1 if failed else 0


def self_test() -> int:
    t = date(2026, 6, 25)
    assert year_range(2003, 2026, t) == list(range(2003, 2027))
    assert year_range(2024, 2030, t) == [2024, 2025, 2026]
    chunks_2025 = iter_year_chunks(2025, 1, t)
    assert len(chunks_2025) == 12
    assert chunks_2025[0].start == date(2025, 1, 1)
    assert chunks_2025[0].end_exclusive == date(2025, 2, 1)
    assert chunks_2025[-1].start == date(2025, 12, 1)
    assert chunks_2025[-1].end_exclusive == date(2026, 1, 1)
    chunks_2026 = iter_year_chunks(2026, 1, t)
    assert len(chunks_2026) == 6
    assert chunks_2026[-1].start == date(2026, 6, 1)
    assert chunks_2026[-1].to_arg == "now"
    cmd = build_cmd(
        binary="dukascopy",
        chunk=chunks_2025[0],
        tmp_dir=Path("tmp"),
        price_type="bid",
        volume_units="millions",
        cli_retries=5,
        retry_pause=5000,
        batch_size=1,
        batch_pause=4000,
        cache=True,
        cache_path=Path("cache"),
        flats=False,
    )
    assert "--batch-size" in cmd and "1" in cmd
    assert "--batch-pause" in cmd and "4000" in cmd
    assert "--retry-pause" in cmd and "5000" in cmd
    assert "--cache" in cmd and "--cache-path" in cmd
    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resilient year-wise 1H XAU/USD downloader for Dukascopy CLI.")
    parser.add_argument("--start-year", type=int, default=2003)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument(
        "--output-dir",
        default="C:/Users/Abhishek Sharma/Desktop/RawPPO/data",
        help="Base data directory. Default is your RawPPO data folder.",
    )
    parser.add_argument("--price-type", default="bid", choices=["bid", "ask", "mid"])
    parser.add_argument("--volume-units", default="millions", choices=["millions", "thousands", "units"])
    parser.add_argument("--chunk-months", type=int, default=1, help="Calendar months per CLI download command. Use 1 for 503-safe mode.")
    parser.add_argument("--batch-size", type=int, default=1, help="Dukascopy CLI parallel downloads per batch. Use 1 for 503-safe mode.")
    parser.add_argument("--batch-pause", type=int, default=4000, help="Dukascopy CLI pause between batches in milliseconds.")
    parser.add_argument("--cli-retries", type=int, default=5, help="Dukascopy CLI retries per internal request.")
    parser.add_argument("--retry-pause", type=int, default=5000, help="Dukascopy CLI pause between internal retries in milliseconds.")
    parser.add_argument("--attempts", type=int, default=6, help="Wrapper-level attempts per chunk.")
    parser.add_argument("--wrapper-pause", type=int, default=20, help="Base seconds for wrapper exponential backoff.")
    parser.add_argument("--timeout", type=int, default=900, help="Seconds per chunk attempt.")
    parser.add_argument("--cache", action=argparse.BooleanOptionalAction, default=True, help="Use Dukascopy CLI cache under <output-dir>/.dukascopy-cache.")
    parser.add_argument("--flats", action="store_true", help="Pass --flats to include zero-volume bars.")
    parser.add_argument("--force", action="store_true", help="Redownload chunks and rebuild years even if final year CSV exists.")
    parser.add_argument("--allow-empty-year", action="store_true", help="Allow a combined year CSV with zero data rows.")
    parser.add_argument("--continue-year-on-chunk-error", action="store_true", help="Try remaining chunks after one chunk fails; final year still marked failed.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned CLI commands only.")
    parser.add_argument("--self-test", action="store_true", help="Run offline logic checks.")
    parser.add_argument("--dukascopy-bin", default=None, help="Path to dukascopy escript, e.g. %USERPROFILE%/.mix/escripts/dukascopy.bat")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.self_test:
        return self_test()

    if not args.dry_run:
        logdir = Path(args.output_dir).expanduser().resolve() / "logs"
        logdir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(logdir / "download_dukascopy_xauusd_1h_resilient.log", encoding="utf-8")
        fh.setLevel(logging.DEBUG if args.verbose else logging.INFO)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logging.getLogger().addHandler(fh)

    return run(args)


if __name__ == "__main__":
    sys.exit(main())
