# Mini OJ

一个简易 Online Judge 项目。后端使用 FastAPI，数据存储使用 SQLite，用户代码通过 Docker 临时容器隔离执行。

当前支持：

- 查看题目
- 力扣模式 Python 代码运行
- 力扣模式 Python 代码提交
- Docker 沙箱评测
- 提交记录查询

用户提交代码时只需要实现 `class Solution` 中的指定方法，不需要自己读取 `input()` 或 `print()`。

## Docker 沙箱评测

`app/judge.py` 的核心行为：

- 使用 `python:3.11-slim` 创建一次性评测容器
- 将用户代码和评测 runner 只读挂载到 `/sandbox`
- 禁用网络访问
- 限制内存、CPU、进程数
- 使用只读根文件系统，并只开放 `/tmp` 临时目录
- 超时自动移除容器并返回 `TLE`
- 根据测试用例返回 `AC`、`WA`、`RE`、`TLE`

评测器会优先使用 Docker 的 CPU quota。如果当前 Docker/cgroup 环境不支持 CPU CFS 限制，容器会降级为不设置 `nano_cpus`，以便开发者仍可在本机复现功能；生产环境建议使用支持 CPU quota 的 Linux/cgroup 配置。

## 环境要求

- Linux/macOS
- Conda 或 Python 3.11
- Docker
- 当前用户可以访问 Docker daemon

## 从零复现

1. 安装 Docker，并确保当前用户可以访问 Docker daemon。

```bash
docker --version
docker ps
```

如果使用 rootless Docker，通常需要让后端进程能访问 rootless socket：

```bash
export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock
```

`app/judge.py` 也会自动尝试读取 `XDG_RUNTIME_DIR/docker.sock` 作为 rootless Docker 的 fallback。

2. 克隆项目。

```bash
git clone https://github.com/prejudicing/mini-oj.git
cd mini-oj
```

3. 使用 Conda 准备后端运行环境。

```bash
conda env create -f environment.yml
conda activate mini-oj
```

如果环境已经存在，可以更新环境：

```bash
conda env update -f environment.yml --prune
conda activate mini-oj
```

如果你不使用 Conda，也可以用 venv 安装同一组依赖。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. 拉取评测镜像。

```bash
docker pull python:3.11-slim
```

5. 启动服务。

```bash
uvicorn app.main:app --reload
```

浏览器打开：

```text
http://127.0.0.1:8000
```

首次启动时会自动创建 SQLite 数据库：

```text
data/submissions.db
```

该文件是运行数据，已被 `.gitignore` 忽略，不需要提交到仓库。

## 常见问题

如果提示 `Address already in use`，说明 8000 端口已经被占用。可以停止已有服务，或换端口启动：

```bash
uvicorn app.main:app --reload --port 8001
```

如果提示 `EnvironmentNameNotFound: Could not find conda environment: mini-oj`，说明还没有创建环境。先执行：

```bash
conda env create -f environment.yml
```

## API

- `GET /problems`：获取题目列表
- `GET /problems/{problem_id}`：获取题目详情
- `POST /run`：运行代码并触发 Docker 评测，不保存提交记录
- `POST /submit`：提交代码并触发 Docker 评测，保存提交记录
- `GET /submissions`：查询最近 50 条提交记录

## 力扣模式

题目使用力扣风格评测。用户只需要实现指定方法：

```python
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        ...
```

评测 runner 会在 Docker 容器内：

1. 导入用户提交的 `solution.py`
2. 创建 `Solution()`
3. 调用题目指定方法
4. 比较方法返回值和预期答案

runner 会预置常用类型名：`List`、`Dict`、`Optional`、`Set`、`Tuple`。因此用户可以像在力扣上一样直接写类型标注。

## 评测模块示例

```python
from app.judge import judge_python_code

result = judge_python_code(
    method_name="twoSum",
    code="""\
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        table = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in table:
                return [table[complement], i]
            table[num] = i
""",
    test_cases=[
        ([[2, 7, 11, 15], 9], [0, 1]),
        ([[3, 2, 4], 6], [1, 2]),
    ],
)

print(result.status)
print(result.stdout)
print(result.stderr)
print(result.execute_time)
```

## 接口验证

服务启动后，可以用下面的命令验证运行接口：

```bash
curl -sS -X POST http://127.0.0.1:8000/run \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "problem_id": 1,
  "code": "class Solution:\n    def twoSum(self, nums: List[int], target: int) -> List[int]:\n        table = {}\n        for i, num in enumerate(nums):\n            complement = target - num\n            if complement in table:\n                return [table[complement], i]\n            table[num] = i\n"
}
JSON
```

预期返回包含：

```json
{"status":"AC"}
```

## 项目结构

```text
mini-oj/
├── app/
│   ├── database.py
│   ├── judge.py
│   ├── main.py
│   ├── models.py
│   └── problems.py
├── data/
│   └── .gitkeep
├── static/
│   ├── app.js
│   ├── index.html
│   └── style.css
├── environment.yml
├── requirements.txt
└── README.md
```

## 注意

本项目依赖本机 Docker daemon。Docker 本身需要较高权限，生产环境还应继续收紧系统层面的隔离策略，例如使用专用低权限用户、独立评测节点、镜像白名单、日志和资源监控。
