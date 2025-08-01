# Commit Message Guidelines

All commit messages should have the following structure:

1. **Title**: A concise yet expressive one-line summary of the change.
2. **Body** consisting of the following sections:
   * `Problem addressed`: Briefly describe the issue or need that prompted the change.
   * `Method of Mitigation`: Summarize the approach taken to solve the problem.
   * `Summary`: List the files affected and provide a short explanation of what was changed in each.
   * `Tests`: Explain what tests were run to verify the changes.
   * `Technical Explanation` (optional): If the change is deep, technical, or complex, provide further details here.

Use clear Markdown formatting for each section so the structure is easy to read.

# Coding Guidelines

Always think twice before you do some potentially breaking changes and rather ask for my feedback than just doing something.
Try to keep your intervals in which you work on your own short (<10min).
If my task is too big, please break it down first and ask me for confirmation that you just do the first step.

# Pre-commit Hook

This repository uses a Git pre-commit hook located in `.githooks/pre-commit`.
It runs `./run_tests.sh` before each commit. If the tests fail, the commit will
be aborted. Review the test output to understand the failure before retrying.
