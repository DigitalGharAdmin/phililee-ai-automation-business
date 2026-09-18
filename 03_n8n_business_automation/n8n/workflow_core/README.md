# Core workflow handoff

Planned name: Business Automation - Inquiry Intake. The authenticated intake follows
the architecture and contracts in `docs/`. Keep configuration client-neutral and
email disabled until acceptance. Existing request IDs branch before AI/logging and
cannot reset approval or email state. Build 2 must test both new and duplicate paths,
all no-send gates and the sending/sent/unknown state transitions. No nodes or live
workflow have been created in Build 1.
