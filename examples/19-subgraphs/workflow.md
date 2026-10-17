# [Config]
- **@trace**: on

# [Node] Draft
[draft] 为用户请求起草一份简洁回答。

## [Transitions]
- @Default -> InitialReview

# [Subgraph] InitialReview
- **@source**: ./review.md

## [Transitions]
- @Default -> Revise

# [Node] Revise
[revise] 根据前面的审查意见修订草稿。

## [Transitions]
- @Default -> FinalReview

# [Subgraph] FinalReview
- **@source**: ./review.md

## [Transitions]
- @Default -> Report

# [Node] Report
[report] 综合两轮审查，给出最终回答。

## [Transitions]
- @Default -> @End
