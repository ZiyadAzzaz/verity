"""Prove that the deployed Cloud Run sandbox identity has no useful project access."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from google.cloud import run_v2

from verity.cloud_handoff import CloudLoggingLineReader
from verity.identity_probe import IDENTITY_LOG_PREFIX, decode_identity_report


def _assert_job_definition(
    job: run_v2.Job,
    expected_service_account: str,
    expected_image: str,
) -> None:
    task = job.template.template
    if task.service_account != expected_service_account:
        raise RuntimeError(
            "sandbox job uses the wrong service account: "
            f"{task.service_account!r} != {expected_service_account!r}"
        )
    if task.volumes:
        raise RuntimeError("sandbox job definition must not declare any mounted volumes")
    if task.vpc_access.connector or task.vpc_access.network_interfaces:
        raise RuntimeError("sandbox job definition must not attach to a VPC network")
    if len(task.containers) != 1:
        raise RuntimeError(
            f"sandbox job definition must contain exactly one container; found {len(task.containers)}"
        )
    for container in task.containers:
        if container.image != expected_image:
            raise RuntimeError(
                f"sandbox job uses the wrong image: {container.image!r} != {expected_image!r}"
            )
        if container.command or container.args:
            raise RuntimeError("sandbox job must use the image's default entrypoint and arguments")
        if container.volume_mounts:
            raise RuntimeError("sandbox container must not declare any volume mounts")
        if container.env:
            names = [variable.name for variable in container.env]
            raise RuntimeError(
                "sandbox job definition must not declare environment variables; found: "
                + ", ".join(names)
            )


def validate(
    *,
    project: str,
    region: str,
    job_name: str,
    expected_service_account: str,
    expected_image: str,
    timeout_seconds: int,
) -> dict[str, object]:
    client = run_v2.JobsClient()
    name = client.job_path(project, region, job_name)
    job = client.get_job(name=name)
    _assert_job_definition(job, expected_service_account, expected_image)

    overrides = run_v2.RunJobRequest.Overrides(
        container_overrides=[
            run_v2.RunJobRequest.Overrides.ContainerOverride(
                args=["--verify-identity", f"{project}:{region}"]
            )
        ],
        task_count=1,
        timeout={"seconds": min(timeout_seconds, 300)},
    )
    operation = client.run_job(request=run_v2.RunJobRequest(name=name, overrides=overrides))
    execution = operation.result(timeout=timeout_seconds)  # type: ignore[no-untyped-call]
    execution_name = execution.name
    line = CloudLoggingLineReader(
        project=project,
        location=region,
        job_name=job_name,
    ).read_line(
        execution_name=execution_name,
        prefix=IDENTITY_LOG_PREFIX,
        timeout_seconds=60,
    )
    report = decode_identity_report(line)
    if report.service_account_email != expected_service_account:
        raise RuntimeError(
            "metadata server exposed the wrong identity: "
            f"{report.service_account_email!r} != {expected_service_account!r}"
        )
    if not report.passed:
        allowed = [
            {
                "service": probe.service,
                "status_code": probe.status_code,
                "detail": probe.detail,
            }
            for probe in report.probes
            if not probe.denied
        ]
        raise RuntimeError(
            "sandbox identity retained project access or a probe was inconclusive: "
            + json.dumps(allowed, ensure_ascii=False)
        )
    return {
        "passed": True,
        "execution": execution_name,
        "service_account": report.service_account_email,
        "metadata_token_obtained": report.metadata_token_obtained,
        "api_denials": {probe.service: probe.status_code for probe in report.probes},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--job", default="verity-sandbox")
    parser.add_argument("--service-account", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--timeout", type=int, default=420)
    arguments = parser.parse_args(argv)
    result = validate(
        project=arguments.project,
        region=arguments.region,
        job_name=arguments.job,
        expected_service_account=arguments.service_account,
        expected_image=arguments.image,
        timeout_seconds=arguments.timeout,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
