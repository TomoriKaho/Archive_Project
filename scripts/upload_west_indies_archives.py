#!/usr/bin/env python3
"""持续把西印度档案 PDF 以可恢复分片上传到 Archive Project。"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import logging
import os
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import ZipFile


LOG = logging.getLogger("west-indies-uploader")
XML_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


@dataclass(frozen=True)
class ArchiveRecord:
    source_id: str
    reference_code: str
    filename: str
    title: str


class ApiError(RuntimeError):
    def __init__(self, status: int, detail: Any):
        super().__init__(f"API {status}: {detail}")
        self.status = status
        self.detail = detail


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            os.environ.setdefault(key, value)


def _column_name(cell_reference: str) -> str:
    return "".join(char for char in cell_reference if char.isalpha())


def _cell_text(cell: ElementTree.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find(f"{XML_NS}v")
    text = value.text if value is not None and value.text is not None else ""
    if cell_type == "s" and text:
        return shared[int(text)]
    if cell_type == "inlineStr":
        return "".join(
            node.text or "" for node in cell.iter(f"{XML_NS}t")
        )
    return text


def read_workbook_records(path: Path) -> dict[str, ArchiveRecord]:
    """只用标准库读取工作簿的 C/D/Q 列，避免服务额外依赖 openpyxl。"""

    if not path.is_file():
        raise FileNotFoundError(f"工作簿不存在: {path}")
    with ZipFile(path) as workbook:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            root = ElementTree.fromstring(
                workbook.read("xl/sharedStrings.xml")
            )
            for item in root.findall(f"{XML_NS}si"):
                shared.append(
                    "".join(
                        node.text or "" for node in item.iter(f"{XML_NS}t")
                    )
                )

        workbook_xml = ElementTree.fromstring(
            workbook.read("xl/workbook.xml")
        )
        relationships = ElementTree.fromstring(
            workbook.read("xl/_rels/workbook.xml.rels")
        )
        targets = {
            node.attrib["Id"]: node.attrib["Target"]
            for node in relationships.findall(f"{PACKAGE_REL_NS}Relationship")
        }
        first_sheet = workbook_xml.find(f"{XML_NS}sheets/{XML_NS}sheet")
        if first_sheet is None:
            raise ValueError("工作簿没有工作表")
        relationship_id = first_sheet.attrib[f"{REL_NS}id"]
        target = targets[relationship_id]
        if target.startswith("/xl/"):
            sheet_path = target.lstrip("/")
        elif target.startswith("xl/"):
            sheet_path = target
        else:
            sheet_path = f"xl/{target.lstrip('/')}"
        sheet = ElementTree.fromstring(workbook.read(sheet_path))

    by_filename: dict[str, ArchiveRecord] = {}
    source_ids: set[str] = set()
    reference_codes: set[str] = set()
    rows = sheet.findall(f".//{XML_NS}sheetData/{XML_NS}row")
    for row in rows[2:]:
        values = {
            _column_name(cell.attrib.get("r", "")): _cell_text(cell, shared)
            for cell in row.findall(f"{XML_NS}c")
        }
        source_id = values.get("C", "").strip()
        reference_code = values.get("Q", "").strip()
        if not source_id or not reference_code:
            continue
        if source_id.endswith(".0") and source_id[:-2].isdigit():
            source_id = source_id[:-2]
        filename = f"{reference_code.replace('/', '_')}.pdf"
        record = ArchiveRecord(
            source_id=source_id,
            reference_code=reference_code,
            filename=filename,
            title=values.get("D", "").strip(),
        )
        if source_id in source_ids:
            raise ValueError(f"工作簿中档案id重复: {source_id}")
        if reference_code in reference_codes:
            raise ValueError(f"工作簿中 Código de referencia 重复: {reference_code}")
        if filename in by_filename:
            raise ValueError(f"斜杠替换后文件名冲突: {filename}")
        source_ids.add(source_id)
        reference_codes.add(reference_code)
        by_filename[filename] = record
    if not by_filename:
        raise ValueError("工作簿中没有可映射的档案记录")
    return by_filename


class UploadState:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                source_id TEXT PRIMARY KEY,
                reference_code TEXT NOT NULL,
                filename TEXT NOT NULL,
                size_bytes INTEGER,
                mtime_ns INTEGER,
                sha256 TEXT,
                remote_upload_id TEXT,
                remote_asset_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                updated_at REAL NOT NULL
            )
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def row(self, source_id: str) -> sqlite3.Row | None:
        self.connection.row_factory = sqlite3.Row
        return self.connection.execute(
            "SELECT * FROM uploads WHERE source_id = ?", (source_id,)
        ).fetchone()

    def save(
        self,
        record: ArchiveRecord,
        *,
        size_bytes: int,
        mtime_ns: int,
        sha256: str | None = None,
        remote_upload_id: str | None = None,
        remote_asset_id: str | None = None,
        status: str,
        error_message: str | None = None,
    ) -> None:
        previous = self.row(record.source_id)
        same_local_file = bool(
            previous
            and previous["size_bytes"] == size_bytes
            and previous["mtime_ns"] == mtime_ns
        )
        self.connection.execute(
            """
            INSERT INTO uploads (
                source_id, reference_code, filename, size_bytes, mtime_ns,
                sha256, remote_upload_id, remote_asset_id, status,
                error_message, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                reference_code = excluded.reference_code,
                filename = excluded.filename,
                size_bytes = excluded.size_bytes,
                mtime_ns = excluded.mtime_ns,
                sha256 = excluded.sha256,
                remote_upload_id = excluded.remote_upload_id,
                remote_asset_id = excluded.remote_asset_id,
                status = excluded.status,
                error_message = excluded.error_message,
                updated_at = excluded.updated_at
            """,
            (
                record.source_id,
                record.reference_code,
                record.filename,
                size_bytes,
                mtime_ns,
                sha256 if sha256 is not None else (
                    previous["sha256"] if same_local_file else None
                ),
                remote_upload_id if remote_upload_id is not None else (
                    previous["remote_upload_id"] if same_local_file else None
                ),
                remote_asset_id if remote_asset_id is not None else (
                    previous["remote_asset_id"] if same_local_file else None
                ),
                status,
                error_message,
                time.time(),
            ),
        )
        self.connection.commit()

    def uploaded_ids(self) -> set[str]:
        return {
            row[0]
            for row in self.connection.execute(
                "SELECT source_id FROM uploads WHERE status = 'uploaded'"
            )
        }


class ArchiveApi:
    def __init__(
        self,
        base_url: str,
        email: str,
        password: str,
        *,
        insecure: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.token: str | None = None
        self.ssl_context = (
            ssl._create_unverified_context() if insecure else ssl.create_default_context()
        )

    def _send(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        content_type: str | None = None,
        authenticated: bool = True,
        timeout: float = 120,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        if data is not None:
            headers["Content-Length"] = str(len(data))
        if authenticated:
            if not self.token:
                self.login()
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(
                request, timeout=timeout, context=self.ssl_context
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw.decode("utf-8"))
                detail = payload.get("detail", payload)
            except (UnicodeDecodeError, json.JSONDecodeError):
                detail = raw.decode("utf-8", errors="replace")
            raise ApiError(exc.code, detail) from exc
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        content_type: str | None = None,
        timeout: float = 120,
    ) -> Any:
        try:
            return self._send(
                method,
                path,
                data=data,
                content_type=content_type,
                timeout=timeout,
            )
        except ApiError as exc:
            if exc.status != 401:
                raise
            self.token = None
            self.login()
            return self._send(
                method,
                path,
                data=data,
                content_type=content_type,
                timeout=timeout,
            )

    def login(self) -> None:
        payload = json.dumps(
            {"email": self.email, "password": self.password}
        ).encode("utf-8")
        response = self._send(
            "POST",
            "/auth/login",
            data=payload,
            content_type="application/json",
            authenticated=False,
        )
        self.token = response["access_token"]

    def resolve_document_uuid(self, title: str) -> str:
        query = urllib.parse.urlencode(
            {"search": title, "limit": 100, "offset": 0}
        )
        response = self.request("GET", f"/documents?{query}")
        items = response.get("items", [])
        exact = [item for item in items if item.get("title") == title]
        if len(exact) == 1:
            return exact[0]["uuid"]
        related = [
            item
            for item in items
            if title in str(item.get("title", ""))
            or str(item.get("title", "")) in title
        ]
        if len(related) == 1:
            LOG.warning(
                "未找到完全同名文档，采用唯一近似结果：%s",
                related[0].get("title"),
            )
            return related[0]["uuid"]
        candidates = [str(item.get("title")) for item in items[:10]]
        raise RuntimeError(
            f"无法唯一确定 document：{title!r}；候选项：{candidates}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    total = path.stat().st_size
    processed = 0
    next_report = 256 * 1024 * 1024
    with path.open("rb") as source:
        while chunk := source.read(4 * 1024 * 1024):
            digest.update(chunk)
            processed += len(chunk)
            if processed >= next_report and total >= next_report:
                LOG.info(
                    "计算哈希 %s: %.1f%%",
                    path.name,
                    processed * 100 / total,
                )
                next_report += 256 * 1024 * 1024
    return digest.hexdigest()


def looks_like_complete_pdf(path: Path) -> bool:
    size = path.stat().st_size
    if size < 8:
        return False
    with path.open("rb") as source:
        if not source.read(5).startswith(b"%PDF-"):
            return False
        source.seek(max(0, size - 1024 * 1024))
        return b"%%EOF" in source.read()


def upload_one(
    api: ArchiveApi,
    document_uuid: str,
    path: Path,
    record: ArchiveRecord,
    state: UploadState,
) -> None:
    stat = path.stat()
    previous = state.row(record.source_id)
    if (
        previous
        and previous["status"] == "uploaded"
        and previous["size_bytes"] == stat.st_size
        and previous["mtime_ns"] == stat.st_mtime_ns
    ):
        return

    digest = None
    if (
        previous
        and previous["size_bytes"] == stat.st_size
        and previous["mtime_ns"] == stat.st_mtime_ns
    ):
        digest = previous["sha256"]
    if not digest:
        LOG.info("计算 SHA-256：%s（%.1f MB）", path.name, stat.st_size / 1048576)
        digest = sha256_file(path)

    state.save(
        record,
        size_bytes=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        sha256=digest,
        status="uploading",
    )
    payload = json.dumps(
        {
            "document_uuid": document_uuid,
            "source_archive_id": record.source_id,
            "filename": record.filename,
            "content_type": "application/pdf",
            "size_bytes": stat.st_size,
            "sha256": digest,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    upload = api.request(
        "POST",
        "/admin/archive-uploads",
        data=payload,
        content_type="application/json",
    )
    upload_id = upload["id"]
    offset = int(upload["received_bytes"])
    chunk_size = int(upload["chunk_size"])
    if upload["status"] == "completed":
        state.save(
            record,
            size_bytes=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            sha256=digest,
            remote_upload_id=upload_id,
            remote_asset_id=upload.get("archive_asset_id"),
            status="uploaded",
        )
        LOG.info("服务端已存在，跳过：%s", path.name)
        return

    LOG.info(
        "开始/恢复上传：%s，偏移 %.1f / %.1f MB",
        path.name,
        offset / 1048576,
        stat.st_size / 1048576,
    )
    next_report = offset + 64 * 1024 * 1024
    with path.open("rb") as source:
        source.seek(offset)
        while offset < stat.st_size:
            chunk = source.read(min(chunk_size, stat.st_size - offset))
            if not chunk:
                raise IOError("本地文件在上传过程中提前结束")
            query = urllib.parse.urlencode({"offset": offset})
            upload = api.request(
                "PUT",
                f"/admin/archive-uploads/{upload_id}/chunk?{query}",
                data=chunk,
                content_type="application/octet-stream",
                timeout=300,
            )
            offset = int(upload["received_bytes"])
            if offset >= next_report or offset == stat.st_size:
                LOG.info(
                    "上传进度 %s: %.1f%%",
                    path.name,
                    offset * 100 / stat.st_size,
                )
                next_report = offset + 64 * 1024 * 1024

    upload = api.request(
        "POST",
        f"/admin/archive-uploads/{upload_id}/complete",
        data=b"",
        content_type="application/json",
        timeout=1800,
    )
    if upload["status"] != "completed":
        raise RuntimeError(f"服务端未完成发布：{upload}")
    state.save(
        record,
        size_bytes=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        sha256=digest,
        remote_upload_id=upload_id,
        remote_asset_id=upload.get("archive_asset_id"),
        status="uploaded",
    )
    LOG.info("上传并发布完成：%s", path.name)


def build_parser() -> argparse.ArgumentParser:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("~/Projects/Scripts/data/西印度档案馆").expanduser(),
    )
    parser.add_argument(
        "--workbook",
        type=Path,
        default=Path(
            "~/Projects/Scripts/Crawler/西印度档案总馆20260722文档.xlsx"
        ).expanduser(),
    )
    parser.add_argument(
        "--api-base",
        default=os.getenv(
            "ARCHIVE_API_BASE_URL", "https://apsr.pku.edu.cn/api"
        ),
    )
    parser.add_argument(
        "--document-title",
        default=os.getenv(
            "ARCHIVE_DOCUMENT_TITLE", "西印度档案总馆20260722"
        ),
    )
    parser.add_argument(
        "--document-uuid", default=os.getenv("ARCHIVE_DOCUMENT_UUID")
    )
    parser.add_argument(
        "--state-db",
        type=Path,
        default=Path(
            "~/.local/state/archive-project/west-indies-uploader.sqlite3"
        ).expanduser(),
    )
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.set_defaults(project_root=project_root)
    return parser


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    load_env_file(project_root / ".env")
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    source_dir = args.source_dir.expanduser().resolve()
    workbook = args.workbook.expanduser().resolve()
    if not source_dir.is_dir():
        LOG.error("PDF 目录不存在：%s", source_dir)
        return 2

    records = read_workbook_records(workbook)
    local_pdfs = list(source_dir.glob("*.pdf"))
    unknown = sorted(path.name for path in local_pdfs if path.name not in records)
    LOG.info(
        "映射审计：工作簿 %d 条，当前 PDF %d 个，未匹配 %d 个",
        len(records),
        len(local_pdfs),
        len(unknown),
    )
    for filename in unknown[:20]:
        LOG.warning("PDF 未出现在工作簿映射中：%s", filename)
    if args.dry_run:
        invalid = [
            path.name
            for path in local_pdfs
            if not path.with_suffix(path.suffix + ".part").exists()
            and not looks_like_complete_pdf(path)
        ]
        LOG.info(
            "PDF 完整性审计：%d 个通过，%d 个未通过",
            len(local_pdfs) - len(invalid),
            len(invalid),
        )
        for filename in invalid[:20]:
            LOG.error("PDF 疑似未完整下载：%s", filename)
        return 1 if unknown or invalid else 0

    email = os.getenv("ARCHIVE_ADMIN_EMAIL") or os.getenv("INITIAL_ADMIN_EMAIL")
    password = os.getenv("ARCHIVE_ADMIN_PASSWORD") or os.getenv(
        "ADMIN_INIT_PASSWORD"
    )
    if not email:
        email = input("管理员邮箱: ").strip()
    if not password:
        password = getpass.getpass("管理员密码: ")
    if not email or not password:
        LOG.error("缺少管理员认证信息")
        return 2

    api = ArchiveApi(
        args.api_base,
        email,
        password,
        insecure=args.insecure,
    )
    document_uuid = args.document_uuid or api.resolve_document_uuid(
        args.document_title
    )
    LOG.info("目标 document UUID：%s", document_uuid)
    state = UploadState(args.state_db.expanduser().resolve())
    warned_incomplete: dict[str, tuple[int, int]] = {}

    try:
        while True:
            uploaded = state.uploaded_ids()
            ready: list[tuple[Path, ArchiveRecord]] = []
            incomplete_count = 0
            for path in source_dir.glob("*.pdf"):
                record = records.get(path.name)
                if not record or record.source_id in uploaded:
                    continue
                previous = state.row(record.source_id)
                stat = path.stat()
                if (
                    previous
                    and previous["status"] == "blocked"
                    and previous["size_bytes"] == stat.st_size
                    and previous["mtime_ns"] == stat.st_mtime_ns
                ):
                    continue
                if path.with_suffix(path.suffix + ".part").exists():
                    incomplete_count += 1
                    continue
                if not looks_like_complete_pdf(path):
                    incomplete_count += 1
                    signature = (stat.st_size, stat.st_mtime_ns)
                    if warned_incomplete.get(path.name) != signature:
                        LOG.warning(
                            "PDF 完整性检查暂未通过，等待文件更新：%s",
                            path.name,
                        )
                        warned_incomplete[path.name] = signature
                    continue
                ready.append((path, record))
            ready.sort(key=lambda item: item[0].stat().st_size)

            for path, record in ready:
                try:
                    upload_one(api, document_uuid, path, record, state)
                except KeyboardInterrupt:
                    raise
                except ApiError as exc:
                    stat = path.stat()
                    permanent = exc.status in {400, 404, 409, 413}
                    state.save(
                        record,
                        size_bytes=stat.st_size,
                        mtime_ns=stat.st_mtime_ns,
                        status="blocked" if permanent else "retry",
                        error_message=str(exc),
                    )
                    LOG.exception("上传失败：%s", path.name)
                except Exception as exc:
                    stat = path.stat()
                    state.save(
                        record,
                        size_bytes=stat.st_size,
                        mtime_ns=stat.st_mtime_ns,
                        status="retry",
                        error_message=str(exc),
                    )
                    LOG.exception("上传失败，下轮继续：%s", path.name)

            uploaded_count = len(state.uploaded_ids() & {
                record.source_id for record in records.values()
            })
            blocked_count = state.connection.execute(
                "SELECT COUNT(*) FROM uploads WHERE status = 'blocked'"
            ).fetchone()[0]
            part_count = sum(1 for _ in source_dir.glob("*.part"))
            LOG.info(
                "总进度：%d/%d 已上传；%d 个阻塞；%d 个 .part；"
                "%d 个等待完整性检查",
                uploaded_count,
                len(records),
                blocked_count,
                part_count,
                incomplete_count,
            )
            if uploaded_count == len(records):
                LOG.info("全部 %d 个档案均已上传，服务正常退出", len(records))
                return 0
            if args.once:
                return 0
            time.sleep(max(args.poll_seconds, 1.0))
    except KeyboardInterrupt:
        LOG.info("收到中断，上传状态已保存，可在下次启动时续传")
        return 130
    finally:
        state.close()


if __name__ == "__main__":
    sys.exit(main())
