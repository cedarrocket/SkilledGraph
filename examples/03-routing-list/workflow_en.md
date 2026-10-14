# [Node] Evaluate

Check whether the available material is sufficient for a report.
Return only enough if sufficient, otherwise insufficient. No explanation or extra content.

## [Transitions]
- enough -> Report
- insufficient -> RequestMaterial

# [Node] Report

Write a concise report from the available material.

## [Transitions]
- @Default -> @End

# [Node] RequestMaterial

Explain which additional material is needed, then let this run finish.

## [Transitions]
- @Default -> @End
