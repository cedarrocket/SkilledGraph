# [Config]
- **@trace**: on

# [Node] Draft
[draft] Draft a concise answer to the user request.

## [Transitions]
- @Default -> InitialReview

# [Subgraph] InitialReview
- **@source**: ./review_en.md

## [Transitions]
- @Default -> Revise

# [Node] Revise
[revise] Revise the draft using the review above.

## [Transitions]
- @Default -> FinalReview

# [Subgraph] FinalReview
- **@source**: ./review_en.md

## [Transitions]
- @Default -> Report

# [Node] Report
[report] Present the final answer using both reviews.

## [Transitions]
- @Default -> @End
