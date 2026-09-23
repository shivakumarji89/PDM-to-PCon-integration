from pathlib import Path

from services.xocd_svn_service import XocdSvnService


def test_svn_override_is_used_for_automated_commands(tmp_path, monkeypatch):
    svn = tmp_path / "svn.exe"
    svn.write_text("", encoding="utf-8")
    monkeypatch.setenv("MK_WORKBENCH_SVN_EXE", str(svn))

    root = tmp_path / "Xocd"
    root.mkdir()
    generated = root / "A.csv"
    generated.write_text("", encoding="utf-8")

    assert XocdSvnService.svn_exe() == svn
    assert XocdSvnService.cleanup_args(root) == [
        str(svn),
        "cleanup",
        "--non-interactive",
        str(root),
    ]
    assert XocdSvnService.update_args(root) == [
        str(svn),
        "update",
        "--non-interactive",
        str(root),
    ]
    assert XocdSvnService.status_args(root, show_updates=True) == [
        str(svn),
        "status",
        "--non-interactive",
        "--show-updates",
        "--xml",
        str(root),
    ]
    assert XocdSvnService.add_args([generated]) == [
        str(svn),
        "add",
        "--non-interactive",
        "--parents",
        str(generated),
    ]
    assert XocdSvnService.commit_args([generated], "Lime - Updating OAS") == [
        str(svn),
        "commit",
        "--non-interactive",
        "--message",
        "Lime - Updating OAS",
        str(generated),
    ]
