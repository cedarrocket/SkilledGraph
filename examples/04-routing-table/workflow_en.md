# [Node] Evaluate

Check whether the available material is sufficient for a report.
Return only enough if sufficient, otherwise insufficient. No explanation or extra content.

## [Transitions]
| Route | Target | Explanation |
| --- | --- | --- |
| enough | Report | Sufficient material |
| insufficient | RequestMaterial | Request more input |

# [Node] Report

Write a concise report from the available material.

## [Transitions]
| Route | Target |
| --- | --- |
| @Default | @End |

# [Node] RequestMaterial

Explain which additional material is needed, then let this run finish.

## [Transitions]
| Route | Target |
| --- | --- |
| @Default | @End |
