from github_repo_stats.services.statistics_service import StatisticsService


def test_aggregate_user_stats_with_data() -> None:
    stats = StatisticsService.aggregate_user_stats(
        commit_rows=[
            {
                "date": "2026-07-13",
                "week": "2026-W28",
                "additions": 10,
                "deletions": 2,
                "total_changes": 12,
            },
            {
                "date": "2026-07-14",
                "week": "2026-W28",
                "additions": 5,
                "deletions": 1,
                "total_changes": 6,
            },
        ],
        file_rows=[
            {"filename": "a.py", "status": "modified", "additions": 5, "deletions": 1, "changes": 6},
            {"filename": "a.py", "status": "modified", "additions": 2, "deletions": 0, "changes": 2},
        ],
        pr_rows=[{"number": 1}],
        issue_rows=[],
        issue_comment_rows=[{"id": 1}],
        pr_comment_rows=[],
    )

    assert stats["total_commits"] == 2
    assert stats["total_additions"] == 15
    assert stats["total_unique_files_changed"] == 1
    assert stats["commits_by_week"] == {"2026-W28": 2}
    assert stats["top_files_by_changes"][0]["filename"] == "a.py"


def test_aggregate_user_stats_without_data() -> None:
    stats = StatisticsService.aggregate_user_stats([], [], [], [], [], [])

    assert stats["total_commits"] == 0
    assert stats["first_commit_date"] == ""
    assert stats["top_files_by_changes"] == []


def test_flatten_insights_handles_empty_or_unexpected_data() -> None:
    assert StatisticsService.flatten_code_frequency(None) == []
    assert StatisticsService.flatten_commit_activity(None) == []
    assert StatisticsService.flatten_participation(None) == []
    assert StatisticsService.flatten_punch_card(None) == []
