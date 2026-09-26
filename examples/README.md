# Try the record helper offline

[English README](../README.md) · [中文说明](../README.zh-CN.md)

For a visual, hands-on product example, open the
[interactive style gallery](showcase/README.md) or the
[note-editor workflow](workflow/README.md). The walkthrough below
focuses on the optional record helper.

For a focused making reference, try the
[choice-and-result study](showcase/README.md#making-study-choice-and-result):
an operable mechanism with content stress cases, source, and applicability
limits, rather than a style to copy wholesale.

The core Frontend Craft skill works without a record store. This example lets
you inspect its optional Python helper using two entirely fictional cases.
It demonstrates retrieval boundaries, not frontend quality or real feedback.
No account, token, package installation, or network request is needed.

Run from the repository root with Python 3 (the CI uses Python 3.13):

```bash
python3 scripts/fc_memory.py validate --root examples/memory
python3 scripts/fc_memory.py query --root examples/memory \
  --project lumen-notes --surface editor --term help
```

Validation returns `status: "valid"` and `case_count: 2`. The query returns
`mode: "lexical"`, `status: "matched"`, and `returned: 1`. Its only candidate is
`lumen-visible-help`. The complete [context.md](memory/context.md) is returned
in `context.text`; keyword matching never trims it. The output also includes
the resolved local `case_store.path`, which varies by checkout.

The candidate keeps `basis: "explicit-feedback"` and `outcome: "rejected"`:
the scenario records a rejection of hover-only help, not acceptance of the
suggested replacement. Both cases are marked synthetic in their own text.
Their field names and allowed values follow the real
[record protocol](../references/memory-operations.md).

Deliberately widen project scope to inspect an analogy:

```bash
python3 scripts/fc_memory.py query --root examples/memory \
  --project lumen-notes --surface editor --term help --transfer
```

This returns two candidates. `orchard-visible-help` has `analogy: true`,
`current_scope.project: "orchard"`, `basis: "hypothesis"`, and
`outcome: "unknown"`. The surface remains `editor`. Transfer does not turn
another project's hypothesis into an accepted preference for Lumen Notes.

A lexical miss is explicit:

```bash
python3 scripts/fc_memory.py query --root examples/memory \
  --project lumen-notes --surface editor --term absent-example-term
```

Expect `status: "no_match"`, `returned: 0`, and the same complete context.
This means no case matched that term; it says nothing about a person's tastes.
All commands above are read-only. The ordinary test suite also exercises these
exact example inputs through the CLI:

```bash
python3 -m unittest discover -s tests -p 'test*.py'
```

For your own records, choose an authorized directory **outside the repository**
and follow [Memory operations](../references/memory-operations.md). Do not edit
the public fixture into a private profile. Optional semantic search and remote
sync have separate [Cloudflare setup and authorization](../references/cloudflare-memory.md).

## 中文速读

这份示例只演示可选 record helper，不是设计质量证明，也不是真实用户反馈。
在 repo 根目录运行上面的命令即可；无需账号、token 或网络。

- 普通查询只返回 `lumen-notes / editor` 的一条案例，并完整返回当前 context。
- 加 `--transfer` 后，额外返回来自 `orchard` 的类比，保留原 scope、假设和未知结果。
- 查不到词时返回 `no_match`，不推断用户没有偏好。

示例全部为合成数据。自己的记录应放在 repo 外明确授权的目录，不能把公开样本
改成私人档案。字段与操作的现行合同见上面链接的 Memory operations。
