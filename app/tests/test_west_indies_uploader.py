from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from app.services.archive_assets import derive_archive_external_key


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "upload_west_indies_archives.py"
)
SPEC = importlib.util.spec_from_file_location("west_indies_uploader", SCRIPT_PATH)
assert SPEC and SPEC.loader
UPLOADER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = UPLOADER
SPEC.loader.exec_module(UPLOADER)


class WestIndiesUploaderTests(unittest.TestCase):
    def test_source_archive_id_is_stable_entry_key(self) -> None:
        self.assertEqual(
            derive_archive_external_key({"档案id": 100154}),
            "100154",
        )

    def test_pdf_completeness_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            complete = Path(directory) / "complete.pdf"
            incomplete = Path(directory) / "incomplete.pdf"
            complete.write_bytes(b"%PDF-1.7\nbody\n%%EOF\n")
            incomplete.write_bytes(b"%PDF-1.7\nbody")
            self.assertTrue(UPLOADER.looks_like_complete_pdf(complete))
            self.assertFalse(UPLOADER.looks_like_complete_pdf(incomplete))

    def test_state_does_not_reuse_hash_after_local_file_changes(self) -> None:
        record = UPLOADER.ArchiveRecord(
            source_id="100154",
            reference_code="ES.41091.AGI//CONTRATACION,5630,N.3",
            filename="ES.41091.AGI__CONTRATACION,5630,N.3.pdf",
            title="test",
        )
        with tempfile.TemporaryDirectory() as directory:
            state = UPLOADER.UploadState(Path(directory) / "state.sqlite3")
            try:
                state.save(
                    record,
                    size_bytes=10,
                    mtime_ns=1,
                    sha256="a" * 64,
                    remote_upload_id="upload-old",
                    status="retry",
                )
                state.save(
                    record,
                    size_bytes=11,
                    mtime_ns=2,
                    status="retry",
                )
                row = state.row(record.source_id)
                self.assertIsNone(row["sha256"])
                self.assertIsNone(row["remote_upload_id"])
            finally:
                state.close()


if __name__ == "__main__":
    unittest.main()
