import os
import time
from datetime import timedelta

from veil.shells.service.checkout_sweep import sweep_old_checkouts


def make_checkout(root, name, age_minutes):
    folder = root / name
    (folder / "repo").mkdir(parents=True)
    (folder / "repo" / "app.py").write_text("x = 1\n")
    stamp = time.time() - age_minutes * 60
    os.utime(folder, (stamp, stamp))
    return folder


def test_it_deletes_the_checkouts_older_than_the_limit_and_keeps_the_new_ones(tmp_path):
    old = make_checkout(tmp_path, "old", 90)
    new = make_checkout(tmp_path, "new", 5)

    removed = sweep_old_checkouts(tmp_path, timedelta(minutes=60))

    assert removed == [old.name]
    assert not old.exists()
    assert new.exists()


def test_it_keeps_a_checkout_that_is_just_inside_the_limit(tmp_path):
    inside = make_checkout(tmp_path, "inside", 59)

    assert sweep_old_checkouts(tmp_path, timedelta(minutes=60)) == []
    assert inside.exists()


def test_a_missing_root_is_not_an_error(tmp_path):
    assert sweep_old_checkouts(tmp_path / "nothing", timedelta(minutes=60)) == []


def test_it_never_follows_a_link_out_of_the_root(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "precious.txt").write_text("keep")
    stamp = time.time() - 7200
    os.utime(outside, (stamp, stamp))
    root = tmp_path / "root"
    root.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)

    sweep_old_checkouts(root, timedelta(minutes=60))

    assert (outside / "precious.txt").read_text() == "keep"


def test_it_leaves_plain_files_alone(tmp_path):
    note = tmp_path / "note.txt"
    note.write_text("hello")
    stamp = time.time() - 7200
    os.utime(note, (stamp, stamp))

    assert sweep_old_checkouts(tmp_path, timedelta(minutes=60)) == []
    assert note.exists()
