# Goals


# vs ControlFlow
- run one task at a time, never multiple
- run one agent at a time, never multiple
- agents have special tools for controling execution: `end_turn()` is default, optionally can also mark tasks successful/failed.
- tasks have a way to indicate whether the answer should be provided via tool or via converfsation e.g. `end_turn()` with no result means take the last message?
- do not recompile conversation history
- for each invocation, store 1) the system message 2) the historical messages