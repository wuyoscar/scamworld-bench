# Docker image

The released image carries the package, all 430 tasks with their websites, Playwright 1.44's Chromium and the fonts the
websites need (Noto core, CJK and emoji). Keys are never in the image.

```bash
docker pull wuyoscar666/scamworld:1.2
docker run --rm wuyoscar666/scamworld:1.2 tasks                         # list the tasks
docker run --rm wuyoscar666/scamworld:1.2 verify prize-07               # scripted browser probes of one task
docker run --rm --network host -v "$PWD/results:/runs" wuyoscar666/scamworld:1.2 \
  run prize-07 --model Qwen/Qwen3-VL-8B-Instruct --base-url http://localhost:8000/v1
docker run --rm -v "$PWD/results:/runs" wuyoscar666/scamworld:1.2 evaluate /runs/sitekit/prize-07 --evaluator rules
```

- `/runs` is the output volume (`results/` inside the container). Mount it to keep the run folders.
- Keys: pass them as environment variables (`-e OPENAI_API_KEY`) and name them with `--api-key-env`, or mount an endpoints
  file (`-v $PWD/configs/endpoints.json:/config/endpoints.json:ro -e SCAMWORLD_ENDPOINTS=/config/endpoints.json`).
  An OpenRouter key file goes to `/config/.env` (`OPENROUTER_API_KEY=...`). `/config/.env.openweights` is an optional
  second OpenRouter key file, read by the judge and by the open-weight models (ids that start with `google/gemma`,
  `qwen/`, `z-ai/`, `deepseek/`, `meta-llama/` or `mistralai/`); when it does not exist, `/config/.env` is used for
  them, so one key file is enough.
- A model server on the host: `--network host` (Linux) or `http://host.docker.internal:<port>/v1` (macOS, Windows).
- Your own tasks ([docs/custom-tasks.md](../../docs/custom-tasks.md)): copy a task of the image into a mounted folder,
  write your request in its `task.json` on your machine, then give the folder's path to `verify` and `run`
  (`--user` makes the copy yours instead of root's on Linux):
  ```bash
  docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/my-tasks:/my-tasks" wuyoscar666/scamworld:1.2 \
    new-task /my-tasks/my-shop-11 --from shop-11
  docker run --rm -v "$PWD/my-tasks:/my-tasks" wuyoscar666/scamworld:1.2 verify /my-tasks/my-shop-11
  ```
  With `-e SCAMWORLD_TASKS=/my-tasks`, `tasks`, `run` and `exp` take the ids of that folder instead of the image's
  tasks (then copy with `--from /scamworld/tasks/shop-11`).
- Your own request or evaluator: mount the folder that holds the file and name it by its path there,
  ```bash
  docker run --rm --network host -v "$PWD:/work" -v "$PWD/results:/runs" wuyoscar666/scamworld:1.2 \
    run shop-11 --model M --base-url http://localhost:8000/v1 \
    --instruction-file /work/request.txt --evaluate /work/my_eval.py:evaluate
  docker run --rm -v "$PWD:/work" -v "$PWD/results:/runs" wuyoscar666/scamworld:1.2 table /runs --evaluator /work/my_eval.py:evaluate
  ```
  `observe`, `signs` and `table` need no model: `docker run --rm wuyoscar666/scamworld:1.2 observe shop-11 --obs ax_tree --grep returns`.
- Your own agent in Python: run it in the image,
  `docker run --rm -v $PWD:/work -v "$PWD/results:/runs" -w /work --entrypoint python wuyoscar666/scamworld:1.2 my_agent.py`
  (runs are written under `/scamworld/results`, which is the `/runs` volume).
- The websites as files:
  ```bash
  docker create --name sw wuyoscar666/scamworld:1.2
  docker cp sw:/scamworld/tasks/. ./tasks && docker cp sw:/scamworld/release/. ./release && docker rm sw
  ```
  (the trailing `/.` copies the contents into `./tasks` and `./release`, new folders or those of a checkout; without it
  an existing folder would get a second one inside. `release/` holds the manifest that `scamworld check`,
  `scamworld verify` and `scamworld exp` verify the tasks against.)

Build it yourself from a checkout (the image then carries the tasks in `tasks/`):

```bash
docker build -f deploy/docker/Dockerfile -t scamworld:1.2 .
docker buildx build --platform linux/amd64,linux/arm64 -f deploy/docker/Dockerfile -t scamworld:1.2 .
```
