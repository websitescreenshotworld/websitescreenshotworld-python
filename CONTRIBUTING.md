# Contributing

Thanks for helping.

- **The API is described once, in the spec.** `spec/` is the
  [websitescreenshotworld-spec](https://github.com/websitescreenshotworld/websitescreenshotworld-spec) repository,
  included as a git submodule fixed to one commit. A change that affects the wire (a new option, field or error
  code) starts there, with a test case; then move this repository's pin with
  `git -C spec checkout <commit>` and commit the new pin together with the code that handles it.
- **The tests run the shared cases.** `spec/conformance/server.js` plays back the cases in `spec/fixtures/`, and the
  test suite runs every case, every webhook vector and every event example.

Clone with the submodule, then install and test (Python 3.10 or later, and Node.js 22 or later for the
conformance server):

```sh
git clone --recurse-submodules https://github.com/websitescreenshotworld/websitescreenshotworld-python.git
cd websitescreenshotworld-python
pip install -e ".[dev]"
ruff format --check . && ruff check . && mypy
pytest
```

Keep pull requests to one change, and add a line to `CHANGELOG.md` under "Unreleased".
