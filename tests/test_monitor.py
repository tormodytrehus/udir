import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import monitor


CALENDAR = """
<html><main>
<h2>November 2026</h2>
<h3>12. nov. Statistikk: Nasjonale prøver <a href="/kalender/prover">Detaljer</a></h3>
<h3>26. nov. Statistikk: Lærlingundersøkelsen</h3>
<h2>Desember 2026</h2>
<h3>10. des. Offentlig publisering av resultat fra Elevundersøkelsen <a href="/kalender/elev">Detaljer</a></h3>
</main></html>
"""

LINKS = """
<html><main>
<a href="/statistikk/nasjonale-prover-2026/">Nasjonale prøver 2026</a>
<a href="/irrelevant/">Noe annet</a>
</main></html>
"""


class MonitorTests(unittest.TestCase):
    def test_calendar_parser_filters_and_dates(self):
        source = {"id": "cal", "title": "Kalender", "url": "https://www.udir.no/kalender/",
                  "terms": ["nasjonale prøver", "elevundersøkelsen"]}
        items = monitor.parse_calendar(CALENDAR, source)
        self.assertEqual([i.due for i in items], ["2026-11-12", "2026-12-10"])
        self.assertTrue(items[0].url.startswith("https://www.udir.no/"))

    def test_link_parser_filters(self):
        source = {"id": "links", "title": "Lenker", "url": "https://www.udir.no/start/",
                  "terms": ["nasjonale prøver"]}
        items = monitor.parse_links(LINKS, source)
        self.assertEqual(len(items), 1)
        self.assertIn("nasjonale-prover-2026", items[0].url)

    def test_silent_baseline_then_due_release(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = {
                "silent_first_run": True,
                "topics": [{"id": "nasjonale-prover", "terms": ["nasjonale prøver"]}],
                "municipalities": [{"number": "5059", "name": "Orkland"}],
                "feed": {"title": "Test", "home_url": "https://www.udir.no/", "description": "Test", "max_items": 10},
                "sources": [{"id": "cal", "title": "Kalender", "kind": "calendar",
                             "url": "https://www.udir.no/kalender/", "terms": ["nasjonale prøver"],
                             "minimum_matches": 1}],
            }
            config_path = root / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            state_path = root / "state.json"
            feed_path = root / "feed.xml"
            fetcher = lambda _: CALENDAR

            first = monitor.run(config_path, state_path, feed_path, today=date(2026, 11, 11),
                                now=datetime(2026, 11, 11, tzinfo=timezone.utc), fetcher=fetcher)
            second = monitor.run(config_path, state_path, feed_path, today=date(2026, 11, 12),
                                 now=datetime(2026, 11, 12, tzinfo=timezone.utc), fetcher=fetcher)
            third = monitor.run(config_path, state_path, feed_path, today=date(2026, 11, 13),
                                now=datetime(2026, 11, 13, tzinfo=timezone.utc), fetcher=fetcher)
            self.assertEqual(first, [])
            self.assertEqual(len(second), 1)
            self.assertEqual(third, [])
            self.assertIn("Orkland", feed_path.read_text(encoding="utf-8"))

    def test_calendar_and_new_link_cannot_double_alert(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = {
                "silent_first_run": True,
                "topics": [{"id": "nasjonale-prover", "terms": ["nasjonale prøver"]}],
                "municipalities": [{"number": "5059", "name": "Orkland"}],
                "feed": {"title": "Test", "home_url": "https://www.udir.no/", "description": "Test", "max_items": 10},
                "sources": [
                    {"id": "cal", "title": "Kalender", "kind": "calendar",
                     "url": "https://www.udir.no/kalender/", "terms": ["nasjonale prøver"], "minimum_matches": 1},
                    {"id": "links", "title": "Statistikk", "kind": "links",
                     "url": "https://www.udir.no/statistikk/", "terms": ["nasjonale prøver"], "minimum_matches": 1},
                ],
            }
            config_path = root / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            state_path, feed_path = root / "state.json", root / "feed.xml"
            pages = {"https://www.udir.no/kalender/": CALENDAR,
                     "https://www.udir.no/statistikk/": LINKS}

            monitor.run(config_path, state_path, feed_path, today=date(2026, 11, 11),
                        now=datetime(2026, 11, 11, tzinfo=timezone.utc), fetcher=pages.__getitem__)
            first_alert = monitor.run(config_path, state_path, feed_path, today=date(2026, 11, 12),
                                      now=datetime(2026, 11, 12, tzinfo=timezone.utc), fetcher=pages.__getitem__)
            pages["https://www.udir.no/statistikk/"] = LINKS.replace(
                "nasjonale-prover-2026", "resultater-nasjonale-prover-2026"
            )
            duplicate = monitor.run(config_path, state_path, feed_path, today=date(2026, 11, 13),
                                    now=datetime(2026, 11, 13, tzinfo=timezone.utc), fetcher=pages.__getitem__)
            self.assertEqual(len(first_alert), 1)
            self.assertEqual(duplicate, [])
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIn("nasjonale-prover:2026", saved["emitted_topics"])

    def test_empty_source_is_rejected(self):
        config = {
            "sources": [{"id": "empty", "title": "Tom", "kind": "links",
                         "url": "https://www.udir.no/", "terms": ["aldri"],
                         "minimum_matches": 1}]
        }
        with self.assertRaises(RuntimeError):
            monitor.collect(config, lambda _: "<html><p>Ingen treff</p></html>")


if __name__ == "__main__":
    unittest.main()
