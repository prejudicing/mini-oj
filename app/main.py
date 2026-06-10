from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.judge import DockerSandboxJudge, JudgeResult, TestCase
from app.models import Submission
from app.problems import get_problem, list_problems


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Mini OJ")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SubmitRequest(BaseModel):
    problem_id: int
    code: str = Field(min_length=1)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/problems")
def problems() -> list[dict[str, object]]:
    return list_problems()


@app.get("/problems/{problem_id}")
def problem_detail(problem_id: int) -> dict[str, object]:
    problem = get_problem(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return {
        "id": problem.id,
        "title": problem.title,
        "difficulty": problem.difficulty,
        "description": problem.description,
        "input_description": problem.input_description,
        "output_description": problem.output_description,
        "examples": problem.examples,
        "hints": problem.hints,
        "template": problem.template,
        "method_name": problem.method_name,
    }


def _judge_problem(problem_id: int, code: str) -> tuple[object, JudgeResult]:
    problem = get_problem(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    result = DockerSandboxJudge().judge(
        code=code,
        method_name=problem.method_name,
        test_cases=[
            TestCase(args=list(case["args"]), expected=case["expected"])
            for case in problem.test_cases
        ],
    )
    return problem, result


@app.post("/run")
def run(payload: SubmitRequest) -> dict[str, object]:
    problem, result = _judge_problem(payload.problem_id, payload.code)
    return {
        "problem_id": problem.id,
        "status": result.status,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "execute_time": result.execute_time,
    }


@app.post("/submit")
def submit(payload: SubmitRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    problem, result = _judge_problem(payload.problem_id, payload.code)

    submission = Submission(
        problem_id=problem.id,
        code=payload.code,
        status=result.status,
        stdout=result.stdout,
        stderr=result.stderr,
        execute_time=result.execute_time,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "id": submission.id,
        "problem_id": submission.problem_id,
        "status": submission.status,
        "stdout": submission.stdout,
        "stderr": submission.stderr,
        "execute_time": submission.execute_time,
        "created_at": submission.created_at.isoformat(),
    }


@app.get("/submissions")
def submissions(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.query(Submission).order_by(Submission.id.desc()).limit(50).all()
    return [
        {
            "id": row.id,
            "problem_id": row.problem_id,
            "code": row.code,
            "status": row.status,
            "stdout": row.stdout,
            "stderr": row.stderr,
            "execute_time": row.execute_time,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
