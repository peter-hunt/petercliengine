"""Tests for profile_manage — CRUD, migration, import/export."""
import json
import pytest
from pathlib import Path
from profile_manage import (
    init_working_folder, get_profiles, load_profile, save_profile,
    delete_profile, profile_exists,
    migrate_save, migrate_saves_in_folder,
    export_profile, import_profile,
)
from models.profile import PlayerProfile, PROFILE_SAVE_VERSION


@pytest.fixture
def workdir(tmp_path):
    """Initialised working directory in a temp folder."""
    init_working_folder(tmp_path)
    return tmp_path


class TestInitWorkingFolder:
    def test_creates_saves_dir(self, tmp_path):
        init_working_folder(tmp_path)
        assert (tmp_path / "saves").is_dir()
        assert (tmp_path / "settings.json").is_file()


class TestSaveLoadDelete:
    def test_save_creates_file(self, workdir):
        p = PlayerProfile(id="hero", name="Hero")
        save_profile(workdir, p)
        assert (workdir / "saves" / "hero.json").exists()

    def test_load_raw_json(self, workdir):
        p = PlayerProfile(id="hero", name="Hero")
        save_profile(workdir, p)
        raw = load_profile(workdir, PlayerProfile, "hero")
        assert isinstance(raw, dict)
        assert raw["id"] == "hero"

    def test_profile_exists(self, workdir):
        p = PlayerProfile(id="hero", name="Hero")
        assert not profile_exists(workdir, "hero")
        save_profile(workdir, p)
        assert profile_exists(workdir, "hero")

    def test_get_profiles(self, workdir):
        save_profile(workdir, PlayerProfile(id="a", name="A"))
        save_profile(workdir, PlayerProfile(id="b", name="B"))
        ids = {pid for _, pid in get_profiles(workdir, PlayerProfile)}
        assert ids == {"a", "b"}

    def test_delete_profile(self, workdir):
        save_profile(workdir, PlayerProfile(id="hero", name="Hero"))
        delete_profile(workdir, "hero")
        assert not profile_exists(workdir, "hero")


class TestMigration:
    def test_migrate_version0_to_1(self):
        obj = {"type": "player_profile", "id": "x", "name": "X"}
        migrated, changed = migrate_save(obj)
        assert changed
        assert migrated["save_version"] == 1

    def test_migrate_current_unchanged(self):
        obj = {"type": "player_profile", "id": "x", "name": "X",
               "save_version": PROFILE_SAVE_VERSION}
        _, changed = migrate_save(obj)
        assert not changed

    def test_migrate_saves_in_folder(self, workdir):
        # Write a legacy save (no save_version key)
        raw = {"type": "player_profile", "id": "old", "name": "Old"}
        (workdir / "saves" / "old.json").write_text(json.dumps(raw))
        count = migrate_saves_in_folder(workdir)
        assert count >= 1
        data = json.loads((workdir / "saves" / "old.json").read_text())
        assert data["save_version"] == 1


class TestImportExport:
    def test_export_creates_archive(self, workdir):
        save_profile(workdir, PlayerProfile(id="hero", name="Hero"))
        out_path = export_profile(workdir, "hero", workdir)
        assert out_path.suffix == ".clisave"
        assert out_path.exists()

    def test_import_restores_profile(self, workdir, tmp_path):
        save_profile(workdir, PlayerProfile(id="hero", name="Hero"))
        archive = export_profile(workdir, "hero", tmp_path)
        dest = tmp_path / "dest"
        init_working_folder(dest)
        pid = import_profile(dest, archive)
        assert pid == "hero"
        assert profile_exists(dest, "hero")

    def test_import_duplicate_raises(self, workdir):
        save_profile(workdir, PlayerProfile(id="hero", name="Hero"))
        archive = export_profile(workdir, "hero", workdir)
        with pytest.raises(FileExistsError):
            import_profile(workdir, archive)

    def test_import_overwrite(self, workdir):
        save_profile(workdir, PlayerProfile(id="hero", name="Hero"))
        archive = export_profile(workdir, "hero", workdir)
        # Should not raise with overwrite=True
        import_profile(workdir, archive, overwrite=True)


class TestProfileSafety:
    def test_unsafe_profile_id_raises(self, workdir):
        with pytest.raises(ValueError):
            profile_exists(workdir, "../unsafe")
        with pytest.raises(ValueError):
            load_profile(workdir, PlayerProfile, "sub/dir")
        with pytest.raises(ValueError):
            delete_profile(workdir, "test\\file")

    def test_save_invalid_id_raises(self, workdir):
        p = PlayerProfile(id="invalid/id", name="Unsafe")
        with pytest.raises(ValueError):
            save_profile(workdir, p)
