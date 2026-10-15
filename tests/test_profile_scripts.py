#!/usr/bin/env python3
"""
Unit and integration tests for profile README scripts:
- Contribution scraper parsing and error handling
- Streak calculation (current streak with today handling, longest streak)
- Monthly aggregations and average calculations
- SVG XML validity for all generated SVGs
- Workflow YAML validity
"""
import os
import sys
import unittest
import xml.etree.ElementTree as ET
import yaml

# Add scripts directory to path
HERE = os.path.dirname(__file__)
SCRIPTS_DIR = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from fetch_contributions import compute_current_streak, compute_longest_streak, build_data
from render_heatmap_svg import render as render_heatmap
from make_info_card import render_info_card


class TestContributionCalculations(unittest.TestCase):
    def test_streaks_with_today_active(self):
        days = [
            {"date": "2026-10-01", "count": 1},
            {"date": "2026-10-02", "count": 2},
            {"date": "2026-10-03", "count": 0},
            {"date": "2026-10-04", "count": 3},
            {"date": "2026-10-05", "count": 4},  # today
        ]
        cur_len, start, end = compute_current_streak(days)
        self.assertEqual(cur_len, 2)
        self.assertEqual(start, "2026-10-04")
        self.assertEqual(end, "2026-10-05")

    def test_streaks_with_today_inactive_but_yesterday_active(self):
        days = [
            {"date": "2026-10-01", "count": 1},
            {"date": "2026-10-02", "count": 2},
            {"date": "2026-10-03", "count": 3},  # yesterday
            {"date": "2026-10-04", "count": 0},  # today in progress
        ]
        cur_len, start, end = compute_current_streak(days)
        self.assertEqual(cur_len, 3)
        self.assertEqual(start, "2026-10-01")
        self.assertEqual(end, "2026-10-03")

    def test_streaks_with_broken_streak(self):
        days = [
            {"date": "2026-10-01", "count": 5},
            {"date": "2026-10-02", "count": 0},
            {"date": "2026-10-03", "count": 0},
        ]
        cur_len, start, end = compute_current_streak(days)
        self.assertEqual(cur_len, 0)
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_longest_streak(self):
        days = [
            {"date": "2026-10-01", "count": 2},
            {"date": "2026-10-02", "count": 1},
            {"date": "2026-10-03", "count": 3},
            {"date": "2026-10-04", "count": 0},
            {"date": "2026-10-05", "count": 1},
        ]
        long_len, start, end = compute_longest_streak(days)
        self.assertEqual(long_len, 3)
        self.assertEqual(start, "2026-10-01")
        self.assertEqual(end, "2026-10-03")

    def test_build_data_zero_division(self):
        days = [
            {"date": "2026-10-01", "count": 0},
            {"date": "2026-10-02", "count": 0},
        ]
        data = build_data(days, username="testuser")
        self.assertEqual(data["total_contributions"], 0)
        self.assertEqual(data["active_days"], 0)
        self.assertEqual(data["avg_per_active_day"], 0.0)

    def test_build_data_with_account_stats(self):
        days = [{"date": "2026-10-01", "count": 1}]
        stats = {
            "public_repos": 20,
            "total_stars": 35,
            "total_prs": 7,
            "merged_prs": 7,
            "commits_365d": 133,
            "code_reviews": 0,
            "total_issues": 1,
        }
        data = build_data(days, username="testuser", account_stats=stats)
        self.assertEqual(data["github_stats"]["public_repos"], 20)
        self.assertEqual(data["github_stats"]["total_prs"], 7)
        self.assertEqual(data["github_stats"]["merged_prs"], 7)
        self.assertEqual(data["github_stats"]["commits_365d"], 133)
        self.assertEqual(data["github_stats"]["code_reviews"], 0)


class TestSVGValidity(unittest.TestCase):
    def test_generated_svgs_are_valid_xml(self):
        assets = [
            os.path.join(HERE, "..", "assets", "contrib-heatmap.svg"),
            os.path.join(HERE, "..", "assets", "ayush-ascii.svg"),
            os.path.join(HERE, "..", "assets", "info-card.svg"),
        ]
        for path in assets:
            self.assertTrue(os.path.exists(path), f"File {path} does not exist")
            try:
                tree = ET.parse(path)
                root = tree.getroot()
                self.assertTrue(root.tag.endswith("svg"), f"Root tag of {path} is not svg")
            except ET.ParseError as err:
                self.fail(f"XML parse error in {path}: {err}")


class TestWorkflowYAML(unittest.TestCase):
    def test_workflow_yaml_syntax(self):
        wf_path = os.path.join(HERE, "..", ".github", "workflows", "update-profile-art.yml")
        self.assertTrue(os.path.exists(wf_path))
        with open(wf_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        self.assertIn("name", content)
        self.assertIn("jobs", content)


if __name__ == "__main__":
    unittest.main()
