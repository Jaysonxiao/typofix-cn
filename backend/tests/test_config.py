from typofix_cn.config import Settings


def test_settings_create_expected_data_paths(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path)
    settings.ensure_directories()
    assert settings.jobs_dir == tmp_path / "jobs"
    assert settings.term_libraries_dir == tmp_path / "term-libraries"
    assert settings.models_dir == tmp_path / "models"
    assert (settings.term_libraries_dir / "default.txt").exists()
    assert settings.confusions_dir == tmp_path / "confusions"
    assert settings.confusions_path == tmp_path / "confusions" / "default.txt"
    assert settings.confusions_path.read_text(encoding="utf-8") == "新资 => 薪资\n"
