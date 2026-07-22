from typofix_cn.domain.jobs import JobStatus
from typofix_cn.jobs.repository import JobRepository


def test_running_jobs_are_marked_interrupted_on_startup(tmp_path) -> None:
    repository = JobRepository(tmp_path)
    manifest = repository.create(["论文.docx"], mode="rules_only", libraries=[])
    repository.update(manifest.model_copy(update={"status": JobStatus.RUNNING}))
    repository.recover_interrupted()
    assert repository.get(manifest.job_id).status == JobStatus.INTERRUPTED


def test_repository_lists_newest_jobs_first(tmp_path) -> None:
    repository = JobRepository(tmp_path)
    first = repository.create(["a.docx"], mode="rules_only", libraries=[])
    second = repository.create(["b.docx"], mode="rules_only", libraries=[])
    assert [item.job_id for item in repository.list()] == [second.job_id, first.job_id]


def test_repository_persists_macbert_thresholds_with_compatible_defaults(tmp_path) -> None:
    repository = JobRepository(tmp_path)

    manifest = repository.create(
        ["a.docx"],
        mode="full",
        libraries=[],
        detection_threshold=0.42,
        correction_threshold=0.18,
    )

    assert manifest.detection_threshold == 0.42
    assert manifest.correction_threshold == 0.18
    assert repository.get(manifest.job_id).model_dump()["detection_threshold"] == 0.42
