# [Node] Explain

- **uses**: ordinary
- @uses: ordinary

```markdown
# [Node] Literal
- **@uses**: python:./missing.py:run
>>> literal
## [Transitions]
- @Default -> @End
```

~~~text
# [Node] AlsoLiteral
~~~

> # [Node] Quoted
> - **@uses**: not-a-setting

- 外层
  - **@uses**: nested

    # [Node] Indented

`- **@uses**: inline`

## [Transitions]
- @Default -> @End
