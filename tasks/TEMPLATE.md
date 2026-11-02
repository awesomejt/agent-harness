# Task card template

Copy the structure into the appropriate phase file. Allocate a stable P ID in PROJECT.md; keep its status only there. This template is not an executable task.

## Task title and stable ID

- **Depends on:** Existing task links plus explicit conditional/selection gates. State whether all prerequisites or an OR condition applies.
- **Deliverable and boundary:** One concrete outcome, owned areas, and explicit limits that prevent the task growing into a framework or unrelated feature.
- **Acceptance evidence:** Tests/fixtures, live evidence if required, versions/platforms, updated docs/decisions and phase acceptance covered.
- **Decision/readiness gate:** Choices needed before work, external prerequisites and candidate-promotion decision if applicable.
- **Contract:** Relevant specification/design/technical contract; canonical status in PROJECT.md.

If the task is too broad for a focused PR, describe sequential substeps or allocate linked child tasks. Preserve the parent acceptance boundary. Use the evidence format and review/merge workflow in README.md.
