"""Context update tool for Claude Code.

Allows Claude Code to update the session context so the permission
reviewer sub-agent can understand what the main agent is doing.

Usage in Claude Code:
  /env CLARITY_TASK="implementing skill hot-loading" CLARITY_TARGET="agents/dispatcher/skills/loader.py"

Or call directly:
  python -m agents.permission_reviewer.context_tool set-task "implementing skill hot-loading"
  python -m agents.permission_reviewer.context_tool set-target "agents/dispatcher/skills/loader.py"
  python -m agents.permission_reviewer.context_tool add-action "modified nodes.py to use skill loader"
  python -m agents.permission_reviewer.context_tool show
"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.permission_reviewer.context import get_session_context, get_recent_changes_analyzer


def cmd_set_task(args):
    """Set the current task."""
    ctx = get_session_context()
    ctx.update_task(args.task, args.target)
    print(f"Task set: {args.task}")
    if args.target:
        print(f"Target file: {args.target}")


def cmd_set_target(args):
    """Set the current target file."""
    ctx = get_session_context()
    current = ctx._context.get("current_task") or "unknown"
    ctx.update_task(current, args.target)
    print(f"Target file set: {args.target}")


def cmd_add_goal(args):
    """Add a goal."""
    ctx = get_session_context()
    goals = ctx._context.get("goals", [])
    goals.append(args.goal)
    ctx.set_goals(goals)
    print(f"Goal added: {args.goal}")


def cmd_add_action(args):
    """Record an action."""
    ctx = get_session_context()
    ctx.add_action(args.action, args.details)
    print(f"Action recorded: {args.action}")


def cmd_add_constraint(args):
    """Add a constraint."""
    ctx = get_session_context()
    ctx.add_constraint(args.constraint)
    print(f"Constraint added: {args.constraint}")


def cmd_show(args):
    """Show current context."""
    ctx = get_session_context()
    print("Current Context:")
    print("=" * 40)
    print(ctx.get_context_summary())

    if args.recent_changes:
        analyzer = get_recent_changes_analyzer()
        changes = analyzer.get_recent_file_changes(minutes=args.minutes)
        print("\nRecently Changed Files:")
        print("-" * 40)
        if changes:
            for c in changes[:10]:
                print(f"  [{c['type']}] {c['path']}")
        else:
            print("  No recent changes")


def cmd_clear(args):
    """Clear the context."""
    ctx = get_session_context()
    ctx.clear()
    print("Context cleared")


def main():
    parser = argparse.ArgumentParser(description="Permission reviewer context tool")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # set-task
    p = subparsers.add_parser("set-task", help="Set current task")
    p.add_argument("task", help="Current task description")
    p.add_argument("--target", "-t", help="Target file")
    p.set_defaults(func=cmd_set_task)

    # set-target
    p = subparsers.add_parser("set-target", help="Set target file")
    p.add_argument("target", help="Target file path")
    p.set_defaults(func=cmd_set_target)

    # add-goal
    p = subparsers.add_parser("add-goal", help="Add a goal")
    p.add_argument("goal", help="Goal description")
    p.set_defaults(func=cmd_add_goal)

    # add-action
    p = subparsers.add_parser("add-action", help="Record an action")
    p.add_argument("action", help="Action description")
    p.add_argument("--details", "-d", help="Additional details")
    p.set_defaults(func=cmd_add_action)

    # add-constraint
    p = subparsers.add_parser("add-constraint", help="Add a constraint")
    p.add_argument("constraint", help="Constraint description")
    p.set_defaults(func=cmd_add_constraint)

    # show
    p = subparsers.add_parser("show", help="Show current context")
    p.add_argument("--recent-changes", "-r", action="store_true", help="Show recent changes")
    p.add_argument("--minutes", "-m", type=int, default=60, help="Minutes to look back")
    p.set_defaults(func=cmd_show)

    # clear
    p = subparsers.add_parser("clear", help="Clear context")
    p.set_defaults(func=cmd_clear)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()