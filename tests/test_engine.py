import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from commit_auto import engine


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True).stdout


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["COMMIT_AUTO_HOME"] = str(self.tmp / "state")
        self.remote = self.tmp / "remote.git"
        self.repo = self.tmp / "repo"
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True)
        sh(self.tmp, "git", "init", "-q", "-b", "main", str(self.repo))
        for key, value in {"user.name": "t", "user.email": "t@t.t"}.items():
            sh(self.repo, "git", "config", key, value)
        (self.repo / "README.md").write_text("hi\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-q", "-m", "init")
        sh(self.repo, "git", "remote", "add", "origin", str(self.remote))

    def tearDown(self):
        os.environ.pop("COMMIT_AUTO_HOME", None)

    def past(self, minutes=2):
        return (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")

    def future(self, minutes=90):
        return (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")

    def test_due_job_commits_and_pushes(self):
        job = engine.add_job(str(self.repo), self.past(), "chore: log", file="log.txt")
        due = engine.run_due()
        self.assertEqual([j["id"] for j in due], [job["id"]])
        self.assertIn("chore: log", (self.repo / "log.txt").read_text())
        pushed = sh(self.remote, "git", "log", "main", "--format=%s")
        self.assertIn("chore: log", pushed)
        self.assertEqual(engine.load_jobs()[0]["status"], "done")

    def test_future_job_waits(self):
        engine.add_job(str(self.repo), self.future(), "later")
        self.assertEqual(engine.run_due(), [])
        self.assertEqual(engine.load_jobs()[0]["status"], "pending")

    def test_backdate_rewrites_timestamp(self):
        stamp = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d 08:00")
        engine.add_job(str(self.repo), stamp, "old entry", file="log.txt",
                       push=False, backdate=True)
        engine.run_due()
        head = sh(self.repo, "git", "log", "-1", "--format=%ad", "--date=format:%Y-%m-%d %H:%M")
        self.assertEqual(head.strip(), stamp)

    def test_delete(self):
        job = engine.add_job(str(self.repo), self.future(), "x", push=False)
        self.assertTrue(engine.delete_job(job["id"]))
        self.assertFalse(engine.delete_job(job["id"]))
        self.assertEqual(engine.load_jobs(), [])

    def test_rejects_non_repo(self):
        with self.assertRaises(ValueError):
            engine.add_job(str(self.tmp), self.future(), "x")

    def test_repeat_reschedules_after_run(self):
        stamp = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
        job = engine.add_job(str(self.repo), stamp, "daily", file="log.txt",
                             push=False, repeat="daily")
        engine.run_due()
        after = engine.load_jobs()[0]
        self.assertEqual(after["status"], "pending")
        self.assertEqual(after["id"], job["id"])
        self.assertEqual(after["attempts"], 0)
        self.assertGreater(datetime.fromisoformat(after["at"]),
                           datetime.fromisoformat(job["at"]) + timedelta(hours=23))

    def test_run_job_ignores_time(self):
        job = engine.add_job(str(self.repo), self.future(), "manual", file="log.txt", push=False)
        self.assertEqual(engine.run_due(), [])
        engine.run_job(job["id"])
        self.assertEqual(engine.load_jobs()[0]["status"], "done")
        self.assertIn("manual", (self.repo / "log.txt").read_text())

    def test_set_repeat_rejects_unknown(self):
        job = engine.add_job(str(self.repo), self.future(), "x", push=False)
        self.assertEqual(engine.set_repeat(job["id"], "weekly")["repeat"], "weekly")
        with self.assertRaises(ValueError):
            engine.set_repeat(job["id"], "hourly")

    def test_bad_time(self):
        with self.assertRaises(ValueError):
            engine.add_job(str(self.repo), "明天", "x")


class I18nTest(unittest.TestCase):
    def test_every_language_matches_english_keys(self):
        from commit_auto.i18n import LANGS, I18N
        base = set(I18N["en"])
        for code, _ in LANGS:
            self.assertIn(code, I18N)
            self.assertEqual(set(I18N[code]), base, f"{code} 缺键或多键")

    def test_at_least_ten_languages(self):
        from commit_auto.i18n import LANGS
        self.assertGreaterEqual(len(LANGS), 10)


if __name__ == "__main__":
    unittest.main()
