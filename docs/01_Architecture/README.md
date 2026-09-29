# Architecture

Current, top-level MK Workbench architecture: the overall system pipeline and the module design for the (planned) generator.

| Document | Covers |
|---|---|
| [System_Architecture.md](./System_Architecture.md) | End-to-end pipeline: PDM SQL Server → Builder Table snapshot → engineering payload → validation → MDB write (`tCOMd_*`) → read-back Workspace Snapshot |
| [Module_Architecture.md](./Module_Architecture.md) | Design for the (future) PCon Generator module |
| [Workflow_Architecture.md](./Workflow_Architecture.md) | **Historical.** Analysis of the former Builder Workspace (`wizard_shell.py`, no longer in the codebase); notes the current analog appears to be `ui/widgets/repository_workspace.py` (`RepositoryWorkspace`), not yet documented with the same rigor |

For the domain concepts these architecture docs operate on (Snapshot, Repository model, Article/Permutation/Pricing/OBX), see [`../02_Domain/`](../02_Domain/).
