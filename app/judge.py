from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import docker
from docker.errors import APIError, DockerException, ImageNotFound
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ReadTimeout


DEFAULT_IMAGE = "python:3.11-slim"


@dataclass(frozen=True)
class TestCase:
    args: list[Any]
    expected: Any


@dataclass(frozen=True)
class JudgeResult:
    status: str
    stdout: str = ""
    stderr: str = ""
    execute_time: float = 0.0


class DockerSandboxJudge:
    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        memory_limit: str = "128m",
        nano_cpus: int = 500_000_000,
        timeout_seconds: float = 3.0,
    ) -> None:
        self.image = image
        self.memory_limit = memory_limit
        self.nano_cpus = nano_cpus
        self.timeout_seconds = timeout_seconds
        self.client = _create_docker_client()

    def judge(self, code: str, method_name: str, test_cases: Iterable[TestCase]) -> JudgeResult:
        cases = list(test_cases)
        if not cases:
            return JudgeResult(status="RE", stderr="No test cases configured.")

        started_at = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="mini-oj-") as tmp:
            workdir = Path(tmp)
            os.chmod(workdir, 0o755)
            self._write_file(workdir / "solution.py", code)
            self._write_file(workdir / "runner.py", _runner_source(method_name, cases))

            try:
                container = self._create_container(workdir, use_cpu_limit=True)
            except ImageNotFound:
                return JudgeResult(
                    status="RE",
                    stderr=f"Docker image not found: {self.image}. Run `docker pull {self.image}` first.",
                )
            except APIError as exc:
                if not _is_unsupported_cpu_limit_error(exc):
                    return JudgeResult(status="RE", stderr=f"Docker error: {exc}")
                try:
                    container = self._create_container(workdir, use_cpu_limit=False)
                except DockerException as retry_exc:
                    return JudgeResult(status="RE", stderr=f"Docker error: {retry_exc}")
            except DockerException as exc:
                return JudgeResult(status="RE", stderr=f"Docker error: {exc}")

            try:
                container.wait(timeout=self.timeout_seconds + 1)
            except (ReadTimeout, RequestsConnectionError):
                self._remove_container(container, force=True)
                return JudgeResult(
                    status="TLE",
                    stderr=f"Execution timed out after {self.timeout_seconds:.1f}s.",
                    execute_time=round(time.monotonic() - started_at, 4),
                )

            raw_logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            self._remove_container(container, force=True)
            execute_time = round(time.monotonic() - started_at, 4)

        return _parse_runner_output(raw_logs, execute_time)

    @staticmethod
    def _write_file(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        os.chmod(path, 0o644)

    def _create_container(self, workdir: Path, use_cpu_limit: bool):
        run_options = {
            "command": ["python", "/sandbox/runner.py"],
            "detach": True,
            "network_disabled": True,
            "mem_limit": self.memory_limit,
            "pids_limit": 64,
            "read_only": True,
            "tmpfs": {"/tmp": "rw,nosuid,nodev,size=16m"},
            "security_opt": ["no-new-privileges"],
            "cap_drop": ["ALL"],
            "user": "65534:65534",
            "working_dir": "/sandbox",
            "volumes": {
                str(workdir): {
                    "bind": "/sandbox",
                    "mode": "ro",
                }
            },
            "environment": {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
            },
        }
        if use_cpu_limit:
            run_options["nano_cpus"] = self.nano_cpus

        return self.client.containers.run(self.image, **run_options)

    @staticmethod
    def _remove_container(container, force: bool = False) -> None:
        try:
            container.remove(force=force)
        except APIError:
            pass


def judge_python_code(
    code: str,
    method_name: str,
    test_cases: Iterable[tuple[list[Any], Any]],
    image: str = DEFAULT_IMAGE,
) -> JudgeResult:
    judge = DockerSandboxJudge(image=image)
    return judge.judge(
        code,
        method_name,
        [TestCase(args=args, expected=expected) for args, expected in test_cases],
    )


def _runner_source(method_name: str, test_cases: list[TestCase]) -> str:
    payload = [
        {
            "args": case.args,
            "expected": case.expected,
        }
        for case in test_cases
    ]
    cases_json = json.dumps(payload, ensure_ascii=False)
    method_json = json.dumps(method_name)
    return f"""\
import importlib.util
import typing
import json
import sys
import time
import traceback

TEST_CASES = {cases_json}
METHOD_NAME = {method_json}


def load_solution():
    spec = importlib.util.spec_from_file_location("solution", "/sandbox/solution.py")
    module = importlib.util.module_from_spec(spec)
    module.__dict__.update({{
        "Dict": typing.Dict,
        "List": typing.List,
        "Optional": typing.Optional,
        "Set": typing.Set,
        "Tuple": typing.Tuple,
    }})
    sys.modules["solution"] = module
    spec.loader.exec_module(module)
    solution_class = getattr(module, "Solution", None)
    if solution_class is None:
        raise AttributeError("Solution class not found")
    return solution_class()


def normalize(value):
    if isinstance(value, tuple):
        return list(value)
    return value


def main():
    started_at = time.monotonic()
    outputs = []

    try:
        solution = load_solution()
        method = getattr(solution, METHOD_NAME)
    except Exception:
        print(json.dumps({{
            "status": "RE",
            "stdout": "",
            "stderr": traceback.format_exc(),
            "execute_time": round(time.monotonic() - started_at, 4),
        }}, ensure_ascii=False))
        return

    for index, case in enumerate(TEST_CASES, start=1):
        try:
            actual = method(*case["args"])
        except Exception:
            print(json.dumps({{
                "status": "RE",
                "stdout": json.dumps(outputs, ensure_ascii=False),
                "stderr": traceback.format_exc(),
                "execute_time": round(time.monotonic() - started_at, 4),
            }}, ensure_ascii=False))
            return

        outputs.append(actual)
        if normalize(actual) != normalize(case["expected"]):
            print(json.dumps({{
                "status": "WA",
                "stdout": json.dumps(actual, ensure_ascii=False),
                "stderr": (
                    f"test case {{index}} expected "
                    f"{{case['expected']!r}}, got {{actual!r}}"
                ),
                "execute_time": round(time.monotonic() - started_at, 4),
            }}, ensure_ascii=False))
            return

    print(json.dumps({{
        "status": "AC",
        "stdout": json.dumps(outputs, ensure_ascii=False),
        "stderr": "",
        "execute_time": round(time.monotonic() - started_at, 4),
    }}, ensure_ascii=False))


if __name__ == "__main__":
    main()
"""


def _parse_runner_output(raw_logs: str, execute_time: float) -> JudgeResult:
    if not raw_logs.strip():
        return JudgeResult(status="RE", stderr="Container produced no output.", execute_time=execute_time)

    last_line = raw_logs.strip().splitlines()[-1]
    try:
        payload = json.loads(last_line)
    except json.JSONDecodeError:
        return JudgeResult(status="RE", stderr=raw_logs, execute_time=execute_time)

    return JudgeResult(
        status=str(payload.get("status", "RE")),
        stdout=str(payload.get("stdout", "")),
        stderr=str(payload.get("stderr", "")),
        execute_time=float(payload.get("execute_time", execute_time)),
    )


def _is_unsupported_cpu_limit_error(exc: APIError) -> bool:
    message = str(exc).lower()
    return "nanocpus can not be set" in message or "cpu cfs scheduler" in message


def _create_docker_client():
    try:
        return docker.from_env()
    except DockerException as first_exc:
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        rootless_socket = Path(runtime_dir or "") / "docker.sock"
        if rootless_socket.exists():
            try:
                return docker.DockerClient(base_url=f"unix://{rootless_socket}")
            except DockerException:
                pass
        raise DockerException(
            "Cannot connect to Docker daemon. Make sure the process user can access "
            "Docker, or set DOCKER_HOST to the correct socket."
        ) from first_exc
