# [Config]
- **@host**: python:./host_cn.py:main

# [Node] ReadCore
- **@uses**: local:read

## [Transitions]
- @Default -> Probe

# [Node] Probe
- **@uses**: local:probe

## [Transitions]
- @Default -> Generate

# [Node] Generate
- **@uses**: local:generate

## [Transitions]
- @Default -> Validate

# [Node] Validate
- **@uses**: local:validate
- **@router**: local:route

## [Transitions]
- passed -> @End
- retry -> Generate
- failed -> @End
