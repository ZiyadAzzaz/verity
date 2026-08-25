from __future__ import annotations

import pytest
from google.cloud import run_v2

from scripts.validate_cloud_sandbox_identity import _assert_job_definition

SERVICE_ACCOUNT = "verity-sandbox@test-project.iam.gserviceaccount.com"
IMAGE = "us-central1-docker.pkg.dev/test-project/verity/verity-sandbox:immutable"


def _job(
    *,
    env: bool = False,
    volume: bool = False,
    command: bool = False,
    vpc: bool = False,
) -> run_v2.Job:
    container = run_v2.Container(image=IMAGE)
    if env:
        container.env = [run_v2.EnvVar(name="ANY_CONFIGURATION", value="unexpected")]
    if command:
        container.command = ["python", "unexpected.py"]
    task = run_v2.TaskTemplate(
        service_account=SERVICE_ACCOUNT,
        containers=[container],
    )
    if volume:
        task.volumes = [
            run_v2.Volume(
                name="unexpected",
                empty_dir=run_v2.EmptyDirVolumeSource(),
            )
        ]
    if vpc:
        task.vpc_access = run_v2.VpcAccess(
            connector="projects/test/locations/us-central1/connectors/private"
        )
    return run_v2.Job(template=run_v2.ExecutionTemplate(template=task))


def test_job_definition_accepts_exact_identity_with_no_env_or_volumes() -> None:
    _assert_job_definition(_job(), SERVICE_ACCOUNT, IMAGE)


@pytest.mark.parametrize(
    "job,match",
    [
        (_job(env=True), "must not declare environment variables"),
        (_job(volume=True), "must not declare any mounted volumes"),
        (_job(command=True), "default entrypoint and arguments"),
        (_job(vpc=True), "must not attach to a VPC network"),
        (_job(), "wrong service account"),
        (_job(), "wrong image"),
    ],
)
def test_job_definition_rejects_ambient_capabilities(job: run_v2.Job, match: str) -> None:
    expected_service_account = (
        "wrong@test-project.iam.gserviceaccount.com"
        if match == "wrong service account"
        else SERVICE_ACCOUNT
    )
    expected_image = "sandbox:wrong" if match == "wrong image" else IMAGE
    with pytest.raises(RuntimeError, match=match):
        _assert_job_definition(job, expected_service_account, expected_image)
