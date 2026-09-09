# SPDX-License-Identifier: Apache-2.0
import argparse
import json
import sys
from pathlib import Path
from dataclasses import replace
from . import __version__
from .analytic import pillbox_tm010
from .config import Case
from .io import save_run
from .rf import quantities
from .solver import solve


def main(argv=None):
    parser = argparse.ArgumentParser(description="Superfish-NG: axisymmetric RF research solver")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ('adaptive-refine','resume-adaptive-refinement','replay-adaptive-refinement'):
        adaptive=sub.add_parser(command,help='run or verify tracked mesh refinement, including version 5 RF confirmation branches')
        adaptive.add_argument('document',type=Path)
        if command!='replay-adaptive-refinement':
            adaptive.add_argument('--out',type=Path,required=True)
            adaptive.add_argument('--max-new-levels',type=int,help='maximum new solves; version 5 includes uniform probes and local solves')
    for command in ('optimize-rf','resume-rf-optimization','replay-rf-optimization'):
        optimization=sub.add_parser(command,help='bounded two-variable native RF constrained search with final refinement')
        optimization.add_argument('document',type=Path)
        if command!='replay-rf-optimization':
            optimization.add_argument('--out',type=Path,required=True)
            optimization.add_argument('--max-new-trials',type=int)
    for command in ('tune','resume-tune','replay-tune'):
        tuning=sub.add_parser(command,help='execute or verify bracketed FEM frequency tuning with identity and refinement checks')
        tuning.add_argument('document',type=Path)
        if command!='replay-tune':
            tuning.add_argument('--out',type=Path,required=True)
            tuning.add_argument('--max-new-trials',type=int)
    for command in ('execute-adaptive-study','resume-adaptive-study','replay-adaptive-study'):
        adaptive=sub.add_parser(command,help='bisect unverified geometry sweep intervals with explicit limits, or replay all decisions')
        adaptive.add_argument('document',type=Path)
        if command!='replay-adaptive-study':
            adaptive.add_argument('--out',type=Path,required=True)
            adaptive.add_argument('--max-new-attempts',type=int)
    for command in ('execute-tracked-study','resume-tracked-study','replay-tracked-study'):
        tracked=sub.add_parser(command,help='execute or verify sequential FEM Study tracking checkpoints')
        tracked.add_argument('document',type=Path)
        if command!='replay-tracked-study':
            tracked.add_argument('--out',type=Path,required=True)
            tracked.add_argument('--max-new-points',type=int)
    study_tracking=sub.add_parser('track-study-modes',help='track adjacent points of a completed native Study without skipping failures')
    study_tracking.add_argument('request',type=Path)
    study_tracking.add_argument('--out',type=Path,required=True)
    study_tracking_replay=sub.add_parser('replay-study-mode-tracking',help='verify Study source identities and recompute ordered correspondence')
    study_tracking_replay.add_argument('document',type=Path)
    for command,help_text in [('start-mode-history','start history from a saved correspondence'),
                              ('extend-mode-history','append a verified saved-field step'),
                              ('replay-mode-history','verify all history sources and ID continuity')]:
        history=sub.add_parser(command,help=help_text)
        history.add_argument('document',type=Path)
        if command=='extend-mode-history':history.add_argument('request',type=Path)
        if command!='replay-mode-history':history.add_argument('--out',type=Path,required=True)
    tracking=sub.add_parser('track-modes',help='track saved PEC modes using an explicit physical or paired-mesh mapping')
    tracking.add_argument('request',type=Path)
    tracking.add_argument('--out',type=Path,required=True)
    tracking_replay=sub.add_parser('replay-mode-tracking',help='recompute and verify saved mode correspondence and source identities')
    tracking_replay.add_argument('tracking',type=Path)
    rf_peaks=sub.add_parser('assess-rf-peaks',help='assess verified native RF discrete peaks and normalization')
    rf_peaks.add_argument('run',type=Path)
    rf_peaks.add_argument('--mode',type=int,default=1,help='one-based rank in this native result, not a persistent identity')
    rf_peaks.add_argument('--out',type=Path,required=True)
    rf_replay=sub.add_parser('replay-rf-peaks',help='revalidate a saved discrete RF peak assessment')
    rf_replay.add_argument('document',type=Path)
    affine_peaks=sub.add_parser('bound-affine-peaks',help='bound continuous discrete PEC peaks of a native affine P1/P2 solution')
    affine_peaks.add_argument('run',type=Path)
    affine_peaks.add_argument('--mode',type=int,default=1,help='one-based frequency rank; not a persistent mode identity')
    affine_peaks.add_argument('--relative-tolerance',type=float,default=1e-6)
    affine_peaks.add_argument('--max-boxes-per-edge',type=int,default=10000)
    affine_peaks.add_argument('--out',type=Path,required=True)
    affine_peak_replay=sub.add_parser('replay-affine-peaks',help='revalidate native affine fields and recompute their saved discrete peak bounds')
    affine_peak_replay.add_argument('document',type=Path)
    affine_surface=sub.add_parser('assess-affine-surface-convergence',help='assess tracked affine refinement peak intervals and polygon corner diagnostics')
    affine_surface.add_argument('checkpoint',type=Path)
    affine_surface.add_argument('--mode-id',required=True)
    affine_surface.add_argument('--out',type=Path,required=True)
    affine_surface_replay=sub.add_parser('replay-affine-surface-convergence',help='revalidate saved affine surface convergence and all native sources')
    affine_surface_replay.add_argument('document',type=Path)
    surface=sub.add_parser('assess-surface-convergence',help='assess tracked fixed-geometry frequency, RF and peak refinement changes')
    surface.add_argument('history',type=Path)
    surface.add_argument('--mode-id',required=True)
    surface.add_argument('--out',type=Path,required=True)
    surface_replay=sub.add_parser('replay-surface-convergence',help='revalidate saved surface convergence and all native sources')
    surface_replay.add_argument('assessment',type=Path)
    tangent = sub.add_parser('construct-tangent', help='preview or explicitly select a tangent in an unfinished curved case')
    tangent.add_argument('request', type=Path)
    tangent.add_argument('--candidate-index', type=int)
    tangent.add_argument('--out', type=Path, required=True, help='new replayable construction JSON')
    diagnosis = sub.add_parser('diagnose-offsets', help='diagnose exact finite normal-offset degeneracies without constructing a case')
    diagnosis.add_argument('request', type=Path)
    diagnosis.add_argument('--out', type=Path, required=True, help='new diagnosis JSON, including unknown cases')
    construction_diagnosis = sub.add_parser('diagnose-construction', help='replay a saved fillet construction or its offset diagnosis and save the diagnosis')
    construction_diagnosis.add_argument('source',type=Path)
    construction_diagnosis.add_argument('--out',type=Path,required=True)
    constructed = sub.add_parser('export-constructed-case', help='replay a tangent construction and export its validated case')
    constructed.add_argument('construction', type=Path)
    constructed.add_argument('--out', type=Path, required=True)
    legacy = sub.add_parser('import-af', help='convert the supported closed-vacuum AF subset to an NG case')
    legacy.add_argument('source', type=Path)
    legacy.add_argument('--out', type=Path, required=True, help='new directory for case, source and conversion report')
    for key in ('nr', 'nz', 'modes'):
        legacy.add_argument('--'+key, type=int, required=True)
    legacy.add_argument('--conductivity-s-per-m', type=float, required=True)
    legacy.add_argument('--normalization-j', type=float, required=True)
    legacy.add_argument('--arc-chord-tolerance-m', type=float, default=1e-5)
    legacy.add_argument('--encoding', choices=['utf-8', 'latin-1'], default='utf-8')
    sub.add_parser('capabilities', help='print currently supported physics and units as JSON')
    migrate = sub.add_parser('migrate-case', help='explicitly migrate a validated case to v3')
    migrate.add_argument('case', type=Path)
    migrate.add_argument('--out', required=True, type=Path, help='new JSON file; must not exist')
    planar_study=sub.add_parser('execute-planar-study',help='execute an independent Cartesian sweep; mode ranks are not tracked IDs')
    planar_study.add_argument('study',type=Path)
    planar_study.add_argument('--out',required=True,type=Path)
    planar_study_replay=sub.add_parser('replay-planar-study',help='fully verify every saved Cartesian sweep point')
    planar_study_replay.add_argument('run',type=Path)
    planar_convergence=sub.add_parser('execute-planar-convergence',help='diagnose same-domain planar mesh refinement; not an error bound')
    planar_convergence.add_argument('request',type=Path)
    planar_convergence.add_argument('--out',required=True,type=Path)
    planar_convergence_replay=sub.add_parser('replay-planar-convergence',help='recompute all saved planar refinement diagnostics')
    planar_convergence_replay.add_argument('run',type=Path)
    planar_history=sub.add_parser('execute-planar-history',help='copy and fully replay an ordered planar tracking history')
    planar_history.add_argument('request',type=Path)
    planar_history.add_argument('--steps',type=Path,nargs='+',required=True)
    planar_history.add_argument('--out',type=Path,required=True)
    planar_history_extend=sub.add_parser('extend-planar-history',help='append a saved pair into a new owned planar history')
    planar_history_extend.add_argument('history',type=Path)
    planar_history_extend.add_argument('next_pair',type=Path)
    planar_history_extend.add_argument('--out',type=Path,required=True)
    planar_history_replay=sub.add_parser('replay-planar-history',help='recompute the full owned planar ancestry and identity chain')
    planar_history_replay.add_argument('run',type=Path)
    planar_tracking=sub.add_parser('execute-planar-tracking',help='track physical electric subspaces between declared rectangle spectra')
    planar_tracking.add_argument('previous',type=Path)
    planar_tracking.add_argument('current',type=Path)
    planar_tracking.add_argument('request',type=Path)
    planar_tracking.add_argument('--out',required=True,type=Path)
    planar_tracking_replay=sub.add_parser('replay-planar-tracking',help='verify both copied native spectra and recompute their correspondence')
    planar_tracking_replay.add_argument('run',type=Path)
    planar_plot=sub.add_parser('plot-planar',help='plot signed Cartesian cutoff fields from verified native coefficients')
    planar_plot.add_argument('run',type=Path)
    planar_plot.add_argument('--out',type=Path,required=True)
    planar_plot.add_argument('--mode',type=int,default=1)
    planar_plot.add_argument('--mesh',action='store_true')
    planar_plot.add_argument('--length-unit',choices=['m','mm'],default='mm')
    planar_project=sub.add_parser('execute-planar-project',help='execute a dedicated Cartesian cutoff Project and verify native completion')
    planar_project.add_argument('project',type=Path)
    planar_project.add_argument('--out',type=Path,required=True)
    planar=sub.add_parser('solve-planar',help='solve an explicit Cartesian vacuum TE/TM cutoff case with J/m normalization')
    planar.add_argument('case',type=Path)
    planar.add_argument('--out',type=Path,required=True)
    planar_replay=sub.add_parser('replay-planar',help='reassemble and verify Cartesian native fields, positive spectrum and per-length RF')
    planar_replay.add_argument('run',type=Path)
    planar_probe=sub.add_parser('probe-planar',help='evaluate verified Cartesian native fields at declared xy points in metres')
    planar_probe.add_argument('run',type=Path)
    planar_probe.add_argument('--points',type=Path,required=True,help='JSON array of [x_m,y_m] points')
    planar_probe.add_argument('--mode',type=int,default=1,help='one-based positive-spectrum index, not a mode label')
    planar_probe.add_argument('--out',type=Path,required=True,help='new CSV file')
    te_replay=sub.add_parser('replay-te',help='verify TE native fields, electric-wall constraints and RF quantities')
    te_replay.add_argument('run',type=Path)
    run = sub.add_parser("solve", help="solve a JSON case and export RF quantities/fields")
    run.add_argument("case", type=Path)
    run.add_argument("--mesh", type=Path, help="explicit SI/rz tagged triangle JSON; replaces case mesh generation")
    run.add_argument("--out", required=True, type=Path, help="new output directory; must not exist")
    run.add_argument("--reflect-full", action="store_true", help="reflect a single symmetry end; export the full cavity at twice the input energy")
    check = sub.add_parser("converge", help="TM010 pillbox refinement benchmark, with exit-code gate")
    check.add_argument("--levels", nargs="+", type=int, default=[8, 16, 32, 64])
    check.add_argument("--out", required=True, type=Path)
    plot = sub.add_parser("plot", help="plot a saved mode and axial/radial probes (requires plot extra)")
    plot.add_argument("run", type=Path)
    plot.add_argument("--out", required=True, type=Path)
    plot.add_argument("--mode", type=int, default=1)
    plot.add_argument("--probe-z-m", type=float)
    plot.add_argument("--mesh", action="store_true")
    gui = sub.add_parser("gui", help="open the local cavity workspace (plot extra required)")
    gui.add_argument("--workspace", type=Path, default=Path("out/gui-workspace"))
    gui.add_argument("--port", type=int, default=0)
    gui.add_argument("--no-browser", action="store_true")
    project = sub.add_parser("run-project", help="solve a shared project or existing case")
    project.add_argument("project", type=Path)
    project.add_argument("--out", type=Path, required=True)
    study = sub.add_parser("study", help="run a saved parameter or refinement study")
    study.add_argument("study", type=Path)
    study.add_argument("--out", type=Path, required=True)
    band = sub.add_parser("band", help="analyze an explicitly declared half-end cell band")
    band.add_argument("run", type=Path)
    band.add_argument("--centers-m", nargs="+", type=float, required=True)
    band.add_argument("--out", type=Path, required=True)
    probe = sub.add_parser("probe", help="export a radial probe from saved fields")
    probe.add_argument("run", type=Path)
    probe.add_argument("--z-m", type=float, required=True)
    probe.add_argument("--mode", type=int, default=1)
    probe.add_argument("--out", type=Path, required=True)
    reference = sub.add_parser("compare-pillbox", help="compare saved cylindrical modes with independent analytical fields and RF")
    reference.add_argument("run", type=Path)
    reference.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ('execute-planar-history','extend-planar-history','replay-planar-history'):
            from .planar_tracking_history import PlanarTrackingHistoryRequest
            from .planar_tracking_history_saved import execute_planar_history,extend_planar_history,read_planar_history
            if args.command=='execute-planar-history':
                result=execute_planar_history(args.steps,PlanarTrackingHistoryRequest.load(args.request),args.out)
            elif args.command=='extend-planar-history':
                result=extend_planar_history(args.history,args.next_pair,args.out)
            else:
                result=read_planar_history(args.run)
            print(json.dumps(result,indent=2,allow_nan=False));return 0
        if args.command in ('execute-planar-tracking','replay-planar-tracking'):
            from .planar_tracking import PlanarTrackingRequest
            from .planar_tracking_jobs import execute_planar_tracking, read_planar_tracking
            result=(execute_planar_tracking(args.previous,args.current,PlanarTrackingRequest.load(args.request),args.out)
                    if args.command=='execute-planar-tracking' else read_planar_tracking(args.run))
            print(json.dumps(result,indent=2,allow_nan=False));return 0
        if args.command in ('execute-planar-convergence','replay-planar-convergence'):
            from .planar_convergence import PlanarConvergence
            from .planar_convergence_jobs import execute_planar_convergence, read_planar_convergence
            result=(execute_planar_convergence(PlanarConvergence.load(args.request),args.out)
                    if args.command=='execute-planar-convergence' else read_planar_convergence(args.run))
            print(json.dumps(result,indent=2,allow_nan=False));return 0
        if args.command in ('execute-planar-study','replay-planar-study'):
            from .planar_study import PlanarStudy
            from .planar_study_jobs import execute_planar_study, read_planar_study
            result=(execute_planar_study(PlanarStudy.load(args.study),args.out) if args.command=='execute-planar-study' else read_planar_study(args.run))
            print(json.dumps(result,indent=2,allow_nan=False))
            return 0
        if args.command=='plot-planar':
            from .planar_visualize import plot_planar_mode
            plot_planar_mode(args.run,args.out,args.mode,args.mesh,args.length_unit)
            print(f'WROTE: {args.out}')
            return 0
        if args.command=='execute-planar-project':
            from .planar_project import PlanarProject
            from .planar_jobs import execute_planar_project
            print(json.dumps(execute_planar_project(PlanarProject.load(args.project),args.out),indent=2,allow_nan=False))
            return 0
        if args.command in ('solve-planar','replay-planar','probe-planar'):
            from .planar import PlanarCase,solve_planar,PlanarFieldSampler
            from .planar_saved import save_planar_run,read_planar_run
            if args.command=='solve-planar':
                from .planar_polygon import load_planar_case
                case=load_planar_case(args.case)
                result=save_planar_run(case,solve_planar(case),args.out)
                print(json.dumps(result,indent=2,allow_nan=False))
            else:
                if args.command=='replay-planar':
                    read_planar_run(args.run)
                    print(f'PASS: {args.run} (Cartesian cutoff; energy J/m; loss W/m)')
                else:
                    from .planar_display import export_planar_probe
                    from .project import parse_json
                    points=parse_json(args.points.read_text(encoding='utf-8'))
                    export_planar_probe(args.run,args.out,points,args.mode)
                    print(f'WROTE: {args.out}')
            return 0
        if args.command in ('execute-adaptive-study','resume-adaptive-study','replay-adaptive-study'):
            from .adaptive_study import execute_adaptive_study,read_adaptive_study
            from .project import parse_json
            if args.command=='execute-adaptive-study':
                result=execute_adaptive_study(parse_json(args.document.read_text(encoding='utf-8')),args.out,max_new_attempts=args.max_new_attempts)
            else:
                result=read_adaptive_study(args.document)
                if args.command=='resume-adaptive-study':
                    result=execute_adaptive_study(result['request'],args.out,max_new_attempts=args.max_new_attempts,checkpoint=result)
            print(f"{result['status']}: {args.document if args.command=='replay-adaptive-study' else args.out}")
            return 1 if result['status']=='UNVERIFIED' else 0
        elif args.command in ('adaptive-refine','resume-adaptive-refinement','replay-adaptive-refinement'):
            from .adaptive_refinement import execute_adaptive_refinement,read_adaptive_refinement
            from .project import parse_json
            if args.command=='adaptive-refine':
                result=execute_adaptive_refinement(parse_json(args.document.read_text(encoding='utf-8')),args.out,max_new_levels=args.max_new_levels)
            else:
                result=read_adaptive_refinement(args.document)
                if args.command=='resume-adaptive-refinement':
                    result=execute_adaptive_refinement(result['request'],args.out,max_new_levels=args.max_new_levels,checkpoint=result)
            print(f"{result['status']}: {args.document if args.command=='replay-adaptive-refinement' else args.out}")
            return 0 if result['status'] in ('TARGETS_MET','PAUSED') else 1
        elif args.command in ('optimize-rf','resume-rf-optimization','replay-rf-optimization'):
            from .rf_optimization import execute_rf_optimization,read_rf_optimization
            from .project import parse_json
            if args.command=='optimize-rf':
                result=execute_rf_optimization(parse_json(args.document.read_text(encoding='utf-8')),args.out,max_new_trials=args.max_new_trials)
            else:
                result=read_rf_optimization(args.document)
                if args.command=='resume-rf-optimization':
                    result=execute_rf_optimization(result['request'],args.out,checkpoint=result,max_new_trials=args.max_new_trials)
            print(f"{result['status']}: {args.document if args.command=='replay-rf-optimization' else args.out}")
            return 0 if result['status'] in ('SEARCH_COMPLETE','PAUSED') else 1
        elif args.command in ('tune','resume-tune','replay-tune'):
            from .tuning import execute_tune,read_tune
            from .project import parse_json
            if args.command=='tune':
                result=execute_tune(parse_json(args.document.read_text(encoding='utf-8')),args.out,max_new_trials=args.max_new_trials)
            else:
                result=read_tune(args.document)
                if args.command=='resume-tune':
                    result=execute_tune(result['request'],args.out,max_new_trials=args.max_new_trials,checkpoint=result)
            print(f"{result['status']}: {args.document if args.command=='replay-tune' else args.out}")
            return 0 if result['status'] in ('TUNED','PAUSED') else 1
        elif args.command in ('execute-tracked-study','resume-tracked-study','replay-tracked-study'):
            from .tracked_study import execute_tracked_study,read_tracked_study
            from .project import parse_json
            if args.command=='execute-tracked-study':
                result=execute_tracked_study(parse_json(args.document.read_text(encoding='utf-8')),args.out,max_new_points=args.max_new_points)
            else:
                result=read_tracked_study(args.document)
                if args.command=='resume-tracked-study':
                    result=execute_tracked_study(result['request'],args.out,max_new_points=args.max_new_points,checkpoint=result)
            print(f"{result['status']}: {args.document if args.command=='replay-tracked-study' else args.out}")
            return 1 if result['status']=='UNVERIFIED' else 0
        elif args.command=='track-study-modes':
            from .study_mode_tracking import save_study_mode_tracking
            from .project import parse_json
            result=save_study_mode_tracking(parse_json(args.request.read_text(encoding='utf-8')),args.out,base_directory=args.request.resolve().parent)
            print(f"{result['status']}: {args.out}")
            return 0 if result['status']=='PASS' else 1
        elif args.command=='replay-study-mode-tracking':
            from .study_mode_tracking import read_study_mode_tracking
            result=read_study_mode_tracking(args.document)
            print(f"REPLAYED {result['status']}: {args.document}")
            return 0 if result['status']=='PASS' else 1
        elif args.command in ('start-mode-history','extend-mode-history','replay-mode-history'):
            from .mode_tracking_history import start_mode_history,extend_mode_history,read_mode_history,save_mode_history
            from .saved_mode_tracking import read_mode_tracking
            from .project import parse_json
            if args.command=='start-mode-history':
                result=save_mode_history(start_mode_history(read_mode_tracking(args.document)),args.out)
            elif args.command=='extend-mode-history':
                request=parse_json(args.request.read_text(encoding='utf-8'))
                result=save_mode_history(extend_mode_history(read_mode_history(args.document),request,
                    base_directory=args.request.resolve().parent),args.out)
            else:result=read_mode_history(args.document)
            print(f"{result['status']}: {getattr(args,'out',args.document)}")
            return 0 if result['status']=='PASS' else 1
        elif args.command == 'track-modes':
            from .saved_mode_tracking import save_mode_tracking
            from .project import parse_json
            result=save_mode_tracking(parse_json(args.request.read_text(encoding='utf-8')),args.out,base_directory=args.request.resolve().parent)
            print(f"{result['status']}: {args.out}")
            return 0 if result['status']=='PASS' else 1
        elif args.command == 'replay-mode-tracking':
            from .saved_mode_tracking import read_mode_tracking
            result=read_mode_tracking(args.tracking)
            print(f"REPLAYED {result['status']}: {args.tracking}")
            return 0 if result['status']=='PASS' else 1
        elif args.command == 'assess-rf-peaks':
            from .rf_peak_assessment import save_rf_peaks
            result=save_rf_peaks(args.run,args.out,mode=args.mode-1)
            print(f"{result['status']}: {args.out}; physical peak convergence unassessed")
            return 0
        elif args.command == 'replay-rf-peaks':
            from .rf_peak_assessment import read_rf_peaks
            result=read_rf_peaks(args.document)
            print(f"REPLAYED {result['status']}: {args.document}")
            return 0
        elif args.command == 'bound-affine-peaks':
            from .affine_extrema import save_affine_peaks
            result=save_affine_peaks(args.run,args.out,mode=args.mode-1,relative_tolerance=args.relative_tolerance,max_boxes_per_edge=args.max_boxes_per_edge)
            print(f"{result['peaks']['status']}: {args.out}; discrete field enclosure only")
            return 0
        elif args.command == 'replay-affine-peaks':
            from .affine_extrema import read_affine_peaks
            result=read_affine_peaks(args.document)
            print(f"REPLAYED {result['peaks']['status']}: {args.document}; discrete field enclosure only")
            return 0
        elif args.command == 'assess-affine-surface-convergence':
            from .affine_surface_convergence import save_affine_surface_convergence
            from .adaptive_refinement import read_adaptive_refinement
            result=save_affine_surface_convergence(read_adaptive_refinement(args.checkpoint),args.mode_id,args.out)
            print(f"{result['status']}: {args.out}; empirical refinement assessment only")
            return 0 if result['status']=='TARGETS_MET' else 1
        elif args.command == 'replay-affine-surface-convergence':
            from .affine_surface_convergence import read_affine_surface_convergence
            result=read_affine_surface_convergence(args.document)
            print(f"REPLAYED {result['status']}: {args.document}")
            return 0 if result['status']=='TARGETS_MET' else 1
        elif args.command == 'assess-surface-convergence':
            from .surface_convergence import save_surface_convergence
            from .mode_tracking_history import read_mode_history
            result=save_surface_convergence(read_mode_history(args.history),args.mode_id,args.out)
            print(f"{result['status']}: {args.out}")
            return 0 if result['status']=='TARGETS_MET' else 1
        elif args.command == 'replay-surface-convergence':
            from .surface_convergence import read_surface_convergence
            result=read_surface_convergence(args.assessment)
            print(f"REPLAYED {result['status']}: {args.assessment}")
            return 0 if result['status']=='TARGETS_MET' else 1
        elif args.command == 'construct-tangent':
            from .tangent_construction import save_construction
            from .project import parse_json
            document = save_construction(parse_json(args.request.read_text(encoding='utf-8')),
                                         args.out, candidate_index=args.candidate_index)
            print(f"{document['status']}: {args.out}")
            return 1 if document['status'] == 'UNVERIFIED' else 0
        elif args.command == 'diagnose-construction':
            from .construction_diagnostics import diagnose_construction,replay_construction_diagnosis
            from .project import parse_json
            source=parse_json(args.source.read_text(encoding='utf-8'))
            document=(replay_construction_diagnosis(source) if isinstance(source,dict) and source.get('document_type')=='construction_offset_diagnosis' else diagnose_construction(source))
            with args.out.open('x',encoding='utf-8') as stream:
                stream.write(json.dumps(document,indent=2,allow_nan=False)+'\n')
            result=document['diagnosis']
            print(f"{result['classification']}: finite_domain_complete={result['finite_domain_complete']}; construction={document['construction']['status']}; {args.out}")
            return 1 if result['status']=='UNVERIFIED' else 0
        elif args.command == 'diagnose-offsets':
            from .offset_degeneracies import diagnose_offsets_document
            from .project import parse_json
            document=diagnose_offsets_document(parse_json(args.request.read_text(encoding='utf-8')))
            with args.out.open('x',encoding='utf-8') as stream:
                stream.write(json.dumps(document,indent=2,allow_nan=False)+'\n')
            result=document['diagnosis']
            print(f"{result['classification']}: finite_domain_complete={result['finite_domain_complete']}; {args.out}")
            return 1 if result['status']=='UNVERIFIED' else 0
        elif args.command == 'export-constructed-case':
            from .tangent_construction import export_constructed_case
            export_constructed_case(args.construction, args.out)
        elif args.command == 'import-af':
            from .legacy_input import import_af
            _, report = import_af(args.source, args.out, encoding=args.encoding, nr=args.nr, nz=args.nz,
                                  modes=args.modes, conductivity_s_per_m=args.conductivity_s_per_m,
                                  normalization_j=args.normalization_j,
                                  arc_chord_tolerance_m=args.arc_chord_tolerance_m)
            print(f'Imported case: {args.out / "case.json"}')
            for diagnostic in report['diagnostics']:
                print(diagnostic)
        elif args.command == 'capabilities':
            from .model import capabilities
            print(json.dumps(capabilities(), indent=2, allow_nan=False))
        elif args.command == 'migrate-case':
            from .model import upgrade_case
            data = upgrade_case(Case.load(args.case).to_dict())
            with args.out.open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(data, indent=2, allow_nan=False) + '\n')
        elif args.command == "gui":
            from .gui import serve
            serve(args.workspace, args.port, not args.no_browser)
        elif args.command == "study":
            from .studies import Study, execute_study
            from .project import parse_json
            study = Study.from_dict(parse_json(args.study.read_text()))
            report = execute_study(study, args.out)
            print(f"study complete; numerical status: {report['numerical_status']}")
            return 1 if report['numerical_status'] == 'FAIL' else 0
        elif args.command == "compare-pillbox":
            from .saved import compare_pillbox
            if args.out.exists():raise ValueError(f"output already exists: {args.out}")
            report = compare_pillbox(args.run)
            with args.out.open('x') as stream:json.dump(report, stream, indent=2, allow_nan=False)
            return 0 if all(m['status']=='PASS' for m in report['modes']) else 1
        elif args.command == "probe":
            from .saved import export_radial_probe
            export_radial_probe(args.run, args.out, args.z_m, args.mode)
        elif args.command == "band":
            from .saved import analyze_band
            if args.out.exists():
                raise ValueError(f"output already exists: {args.out}")
            report = analyze_band(args.run, args.centers_m)
            with args.out.open('x') as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
        elif args.command == "run-project":
            from .project import Project
            from .jobs import execute_project
            result = execute_project(Project.load(args.project), args.out)
            print(f"{result['status']}: {args.out}")
        elif args.command == 'replay-te':
            from .te_saved import read_te_run
            from .te import te_quantities
            solution=read_te_run(args.run)
            print(json.dumps({'status':'PASS','modes':[te_quantities(solution,i) for i in range(solution.case.modes)]},indent=2))
        elif args.command == "solve":
            if args.out.exists():
                raise ValueError(f"output already exists: {args.out}; choose a new directory")
            case = Case.load(args.case)
            mesh_data = None
            if args.mesh is not None:
                from .project import parse_json
                mesh_data = parse_json(args.mesh.read_text(encoding='utf-8'))
            solution = solve(case, mesh_data=mesh_data)
            if args.reflect_full:
                from .symmetry import reflect_solution
                case, solution = reflect_solution(case, solution)
            result = save_run(case, solution, args.out)
            for mode in result["modes"]:
                if case.model is not None and case.model.polarization=='te':
                    print(f"TE mode {mode['mode_index']}: {mode['frequency_hz']/1e6:.6f} MHz, Q0={mode['q0']:.3f}, axial R/Q=N/A")
                    continue
                print(f"Mode {mode['mode_index']}: {mode['frequency_hz']/1e6:.6f} MHz, "
                      f"Q0={mode['q0']:.3f}, R/Q(acc)={mode['r_over_q_accelerator_ohm']:.6f} ohm")
        elif args.command == "plot":
            try:
                from .visualize import plot_mode
            except ImportError as exc:
                raise ValueError("plotting requires the optional dependencies: pip install -e '.[plot]'") from exc
            plot_mode(args.run, args.out, args.mode, args.probe_z_m, args.mesh)
        else:
            if args.out.exists():
                raise ValueError(f"output already exists: {args.out}")
            if len(args.levels) < 2 or any(n < 2 for n in args.levels) or any(b <= a for a, b in zip(args.levels, args.levels[1:])):
                raise ValueError("levels must be at least two strictly increasing integers >= 2")
            base = Case(((0., .1), (.2, .1)), modes=1)
            exact = pillbox_tm010(.1, .2)
            rows = []
            for n in args.levels:
                case = replace(base, nr=n, nz=n)
                solution = solve(case)
                q = quantities(case, solution)
                rows.append({"nr": n, "nz": n, "nodes": len(solution.mesh.points), "quantities": q,
                             "relative_errors": {k: abs(q[k]/v-1) for k, v in exact.items() if v is not None and v != 0}})
                print(f"n={n}: f={q['frequency_hz']/1e6:.9f} MHz, relative error={rows[-1]['relative_errors']['frequency_hz']:.3g}")
            freq = [r["relative_errors"]["frequency_hz"] for r in rows]
            gates = {"frequency_finest_below_1e-4": freq[-1] < 1e-4,
                     "frequency_error_decreases": all(b < a for a, b in zip(freq, freq[1:])),
                     "rq_finest_below_0_005": rows[-1]["relative_errors"]["r_over_q_accelerator_ohm"] < .005,
                     "q0_finest_below_0_005": rows[-1]["relative_errors"]["q0"] < .005}
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps({"benchmark": "pillbox TM010 R=.1 L=.2 beta=1 sigma=5.8e7", "analytic": exact,
                                           "rows": rows, "gates": gates, "passed": all(gates.values())}, indent=2, allow_nan=False)+"\n")
            return 0 if all(gates.values()) else 1
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
