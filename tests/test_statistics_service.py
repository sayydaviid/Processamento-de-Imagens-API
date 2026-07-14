from github_repo_stats.services.statistics_service import StatisticsService


def _commit_detail(
    authored_at: str,
    additions: int,
    deletions: int,
    total: int,
    parents: int = 1,
) -> dict:
    return {
        "commit": {
            "author": {"date": authored_at},
            "committer": {"date": authored_at},
        },
        "stats": {
            "additions": additions,
            "deletions": deletions,
            "total": total,
        },
        "parents": [{} for _ in range(parents)],
    }


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


def test_manual_repository_statistics_group_by_sunday_week_and_skip_merges() -> None:
    manual = StatisticsService.build_manual_repository_statistics_from_commit_details(
        [
            _commit_detail("2026-07-12T10:00:00Z", additions=10, deletions=2, total=12),
            _commit_detail("2026-07-13T10:00:00Z", additions=5, deletions=3, total=8),
            _commit_detail("2026-07-14T10:00:00Z", additions=100, deletions=100, total=200, parents=2),
            _commit_detail("2026-07-19T10:00:00Z", additions=1, deletions=1, total=2),
        ]
    )

    assert manual["skipped_merge_commits"] == 1

    activity_rows = manual["commit_activity_rows"]
    assert len(activity_rows) == 2
    assert activity_rows[0]["week_start"] == "2026-07-12"
    assert activity_rows[0]["total"] == 2
    assert activity_rows[0]["sunday"] == 1
    assert activity_rows[0]["monday"] == 1
    assert activity_rows[0]["tuesday"] == 0
    assert activity_rows[1]["week_start"] == "2026-07-19"
    assert activity_rows[1]["sunday"] == 1

    frequency_rows = manual["code_frequency_rows"]
    assert frequency_rows[0]["week_start"] == "2026-07-12"
    assert frequency_rows[0]["additions"] == 15
    assert frequency_rows[0]["deletions"] == 5
    assert frequency_rows[0]["total_changes"] == 20

    code_frequency_api_like = manual["code_frequency_api_like"]
    assert code_frequency_api_like[0] == [frequency_rows[0]["week_timestamp"], 15, -5]

    commit_activity_api_like = manual["commit_activity_api_like"]
    assert commit_activity_api_like[0]["week"] == activity_rows[0]["week_timestamp"]
    assert commit_activity_api_like[0]["days"] == [1, 1, 0, 0, 0, 0, 0]
