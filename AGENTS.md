# Agent Instructions

## Work tracking

Work lives in hosted issues. Use full references such as
`sussdorff/fmcli#123` with `ccore tracker`.

```bash
ccore tracker list --repo sussdorff/fmcli
ccore tracker show sussdorff/fmcli#123
```

## Session Completion

Complete the required verification and review before publication or merge.
Report the pull request, its merge state, verification results and any remaining
blockers. Preserve existing authorization for the same concrete scope, and do
not remove foreign or dirty worktrees.
