# Windows Bridge

This branch contains a local Windows worker for controlled development tasks.

The normal checkout at C:\ai\AutonomousIncomeAgent_GitHub remains on main. The installer creates a separate worktree at C:\AI_WindowsBridge.

Security boundaries:
- File access is restricted to C:\AI_System and the configured project workspace.
- Remote process execution is limited to an explicit executable allow-list.
- The worker does not use shell=True, cmd.exe, or remote PowerShell.
- Write/delete/mkdir/run operations require a local ARMED switch.
- Secrets and account credentials must never be placed in bridge commands.
