# SPDX-License-Identifier: Apache-2.0
"""Explicit CLI registration and execution for the owned curved Hphi tune group."""
from pathlib import Path

COMMANDS = ('tune-curved-hphi', 'resume-tune-curved-hphi', 'replay-tune-curved-hphi')


def register_arguments(subparsers, command):
    """Register one declared command, preserving its place in the main help."""
    if command not in COMMANDS:
        raise ValueError('expected a curved Hphi tuning command')
    sub = subparsers
    tuning=sub.add_parser(command,help='execute or verify bracketed FEM frequency tuning with identity and refinement checks')
    tuning.add_argument('document',type=Path)
    if command != 'replay-tune-curved-hphi':
        tuning.add_argument('--out',type=Path,required=True)
        tuning.add_argument('--max-new-trials',type=int)


def execute(args):
    """Execute the declared tune/replay/resume operation; main owns errors."""
    from .curved_hphi_tuning_saved import execute_curved_hphi_tune,read_curved_hphi_tune
    from .project import parse_json
    if args.command=='tune-curved-hphi':
        result=execute_curved_hphi_tune(parse_json(args.document.read_text(encoding='utf-8')),args.out,max_new_trials=args.max_new_trials)
    else:
        result=read_curved_hphi_tune(args.document)
        if args.command=='resume-tune-curved-hphi':
            result=execute_curved_hphi_tune(result['request'],args.out,max_new_trials=args.max_new_trials,checkpoint=result)
    print(f"{result['status']}: {args.document if args.command=='replay-tune-curved-hphi' else args.out}")
    return 0 if result['status'] in ('TUNED','PAUSED') else 1
