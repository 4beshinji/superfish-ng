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
    freeze=sub.add_parser('freeze-curved-refinement',help='capture marked quadratic split choices in a new explicit-source Project')
    freeze.add_argument('project',type=Path)
    freeze.add_argument('--out',type=Path,required=True)
    deform=sub.add_parser('deform-curved-project',help='move a fixed numbered curved mesh to a declared target geometry using harmonic displacement')
    deform.add_argument('project',type=Path)
    deform.add_argument('--geometry',type=Path,required=True,help='native curved_contour geometry JSON, with matching ordered curves/tags')
    deform.add_argument('--rf-coordinates',choices=('fixed','axis_fraction'),required=True)
    deform.add_argument('--minimum-corner-angle-deg',type=float,required=True)
    deform.add_argument('--out',type=Path,required=True)
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
    hphi_tracking=sub.add_parser('execute-hphi-tracking',help='compare original Hphi E/H subspaces on the same vacuum with explicit comparison meshes')
    hphi_tracking.add_argument('previous',type=Path);hphi_tracking.add_argument('current',type=Path)
    hphi_tracking.add_argument('request',type=Path);hphi_tracking.add_argument('--out',type=Path,required=True)
    hphi_tracking_replay=sub.add_parser('replay-hphi-tracking',help='fully replay both owned Hphi spectra and their subspace correspondence')
    hphi_tracking_replay.add_argument('run',type=Path)
    hphi_convergence=sub.add_parser('execute-hphi-convergence',help='solve an explicit same-domain mesh sequence and compare original Hphi E/H/RF differences')
    hphi_convergence.add_argument('request',type=Path);hphi_convergence.add_argument('--out',type=Path,required=True)
    hphi_convergence_replay=sub.add_parser('replay-hphi-convergence',help='fully replay every Hphi mesh level and finite-difference decision')
    hphi_convergence_replay.add_argument('run',type=Path)
    hphi_study=sub.add_parser('execute-hphi-study',help='execute independent Hphi spectra; ranks are not tracked IDs')
    hphi_study.add_argument('study',type=Path);hphi_study.add_argument('--out',type=Path,required=True)
    hphi_study_replay=sub.add_parser('replay-hphi-study',help='fully verify every saved independent Hphi point and summary')
    hphi_study_replay.add_argument('run',type=Path)
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
    hphi_history=sub.add_parser('execute-hphi-history',help='copy and fully replay an ordered hphi tracking history')
    hphi_history.add_argument('request',type=Path)
    hphi_history.add_argument('--steps',type=Path,nargs='+',required=True)
    hphi_history.add_argument('--out',type=Path,required=True)
    hphi_history_extend=sub.add_parser('extend-hphi-history',help='append a saved pair into a new owned hphi history')
    hphi_history_extend.add_argument('history',type=Path)
    hphi_history_extend.add_argument('next_pair',type=Path)
    hphi_history_extend.add_argument('--out',type=Path,required=True)
    hphi_history_replay=sub.add_parser('replay-hphi-history',help='recompute the full owned hphi ancestry and identity chain')
    hphi_history_replay.add_argument('run',type=Path)
    planar_tracking=sub.add_parser('execute-planar-tracking',help='track physical electric subspaces under a declared rectangle or polygon mapping')
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
    hphi_plot=sub.add_parser('plot-hphi',help='plot signed original-cell Hphi/Er/Ez fields, omitting conductor holes')
    hphi_plot.add_argument('run',type=Path)
    hphi_plot.add_argument('--out',type=Path,required=True)
    hphi_plot.add_argument('--mode',type=int,default=1)
    hphi_plot.add_argument('--mesh',action='store_true')
    hphi_plot.add_argument('--length-unit',choices=('m','mm'),default='mm')
    hphi_csv=sub.add_parser('probe-hphi-csv',help='export all signed cylindrical E/H/B components in SI CSV with native metadata')
    hphi_csv.add_argument('run',type=Path)
    hphi_csv.add_argument('--out',type=Path,required=True)
    hphi_csv.add_argument('--points',type=Path,required=True)
    hphi_csv.add_argument('--mode',type=int,default=1)
    hphi_project=sub.add_parser('execute-hphi-project',help='execute a dedicated regular-axis or positive-radius Hphi Project with verified native completion')
    hphi_project.add_argument('project',type=Path)
    hphi_project.add_argument('--out',type=Path,required=True)
    curved_hphi=sub.add_parser('solve-curved-hphi',help='solve an explicit quadratic vacuum Hphi geometry with verified native output')
    curved_hphi.add_argument('case',type=Path);curved_hphi.add_argument('--out',required=True,type=Path)
    curved_hphi_replay=sub.add_parser('replay-curved-hphi',help='reconstruct curved geometry, lowest positive FEM and all RF, and emit verified JSON')
    curved_hphi_replay.add_argument('run',type=Path)
    curved_hphi_probe=sub.add_parser('probe-curved-hphi',help='export original signed E/H/B fields at curved vacuum [r_m,z_m] points')
    curved_hphi_probe.add_argument('run',type=Path);curved_hphi_probe.add_argument('--points',required=True,type=Path)
    curved_hphi_probe.add_argument('--mode',type=int,default=1,help='one-based positive-spectrum rank, not a mode identity')
    curved_hphi_probe.add_argument('--out',required=True,type=Path)
    electrostatic=sub.add_parser('solve-electrostatic',help='solve an explicit axisymmetric dielectric/electrode Poisson case with verified native output')
    electrostatic.add_argument('case',type=Path);electrostatic.add_argument('--out',required=True,type=Path)
    electrostatic_replay=sub.add_parser('replay-electrostatic',help='reconstruct static materials, signed charges, electrode boundary conditions, Phi/E/D and all integral quantities')
    electrostatic_replay.add_argument('run',type=Path)
    electrostatic_probe=sub.add_parser('probe-electrostatic',help='export original static Phi/E/D at dielectric [r_m,z_m] points with one-sided region metadata')
    electrostatic_probe.add_argument('run',type=Path);electrostatic_probe.add_argument('--points',required=True,type=Path)
    electrostatic_probe.add_argument('--out',required=True,type=Path)
    planar_electrostatic=sub.add_parser('solve-planar-electrostatic',help='solve an explicit planar dielectric/electrode Poisson case with verified native output')
    planar_electrostatic.add_argument('case',type=Path);planar_electrostatic.add_argument('--out',required=True,type=Path)
    planar_electrostatic_replay=sub.add_parser('replay-planar-electrostatic',help='reconstruct static materials, signed charges, electrode boundary conditions, Phi/E/D and all integral quantities')
    planar_electrostatic_replay.add_argument('run',type=Path)
    planar_electrostatic_probe=sub.add_parser('probe-planar-electrostatic',help='export original static Phi/E/D at dielectric [x_m,y_m] points with one-sided region metadata')
    planar_electrostatic_probe.add_argument('run',type=Path);planar_electrostatic_probe.add_argument('--points',required=True,type=Path)
    planar_electrostatic_probe.add_argument('--out',required=True,type=Path)
    axial_force=sub.add_parser('analyze-off-axis-magnetic-force',help='integrate verified full-ring axial force [N], optionally with actual axial FEM displacements')
    axial_force.add_argument('run',type=Path);axial_force.add_argument('--request',required=True,type=Path);axial_force.add_argument('--out',required=True,type=Path)
    axial_force_replay=sub.add_parser('replay-off-axis-magnetic-force',help='replay positive-radius axial force source, stress and requested full-ring work')
    axial_force_replay.add_argument('run',type=Path);axial_force_replay.add_argument('report',type=Path)
    magnetic_force=sub.add_parser('analyze-planar-magnetic-force',help='integrate original planar Maxwell force and two torque definitions, optionally with displaced-FEM work')
    magnetic_force.add_argument('run',type=Path);magnetic_force.add_argument('--request',required=True,type=Path);magnetic_force.add_argument('--out',required=True,type=Path)
    magnetic_force_replay=sub.add_parser('replay-planar-magnetic-force',help='verify force source, body, vacuum weights, original stress and all requested displaced FEM cases')
    magnetic_force_replay.add_argument('run',type=Path);magnetic_force_replay.add_argument('report',type=Path)
    magnetic_multipoles=sub.add_parser('extract-planar-magnetic-multipoles',help='extract source-free planar magnetic harmonics from a verified native run')
    magnetic_multipoles.add_argument('run',type=Path);magnetic_multipoles.add_argument('--request',required=True,type=Path);magnetic_multipoles.add_argument('--out',required=True,type=Path)
    magnetic_multipoles_replay=sub.add_parser('replay-planar-magnetic-multipoles',help='verify the source native, original FEM circles, multipole coefficients and diagnostics')
    magnetic_multipoles_replay.add_argument('run',type=Path);magnetic_multipoles_replay.add_argument('report',type=Path)
    planar_magnetostatic=sub.add_parser('solve-planar-magnetostatic',help='solve an explicit planar magnetic/current Az case with verified native output')
    planar_magnetostatic.add_argument('case',type=Path);planar_magnetostatic.add_argument('--out',required=True,type=Path)
    planar_magnetostatic_replay=sub.add_parser('replay-planar-magnetostatic',help='reconstruct magnetic materials, signed currents, Az/Ht boundaries, Az/B/H and all integral quantities')
    planar_magnetostatic_replay.add_argument('run',type=Path)
    planar_magnetostatic_probe=sub.add_parser('probe-planar-magnetostatic',help='export original static Az/B/H at magnetic-domain [x_m,y_m] points with one-sided region metadata')
    planar_magnetostatic_probe.add_argument('run',type=Path);planar_magnetostatic_probe.add_argument('--points',required=True,type=Path)
    planar_magnetostatic_probe.add_argument('--out',required=True,type=Path)
    planar_recoil=sub.add_parser('solve-planar-recoil',help='solve an explicit planar recoil tensor/remanence/current Az case with verified native output')
    planar_recoil.add_argument('case',type=Path);planar_recoil.add_argument('--out',required=True,type=Path)
    planar_recoil_replay=sub.add_parser('replay-planar-recoil',help='reconstruct recoil tensors, remanent induction, signed currents, Az/Ht boundaries, Az/B/H and all integral quantities')
    planar_recoil_replay.add_argument('run',type=Path)
    planar_recoil_probe=sub.add_parser('probe-planar-recoil',help='export original static Az/B/H at magnetic-domain [x_m,y_m] points with one-sided region metadata')
    planar_recoil_probe.add_argument('run',type=Path);planar_recoil_probe.add_argument('--points',required=True,type=Path)
    planar_recoil_probe.add_argument('--out',required=True,type=Path)
    planar_bh=sub.add_parser('solve-planar-bh',help='solve an explicit planar nonlinear B-H/current Az case with verified success or retained failure output')
    planar_bh.add_argument('case',type=Path);planar_bh.add_argument('--out',required=True,type=Path)
    planar_bh_replay=sub.add_parser('replay-planar-bh',help='reconstruct B-H curves, Newton histories, signed currents, Az/Ht boundaries, Az/B/H and all integral quantities')
    planar_bh_replay.add_argument('run',type=Path)
    planar_bh_probe=sub.add_parser('probe-planar-bh',help='export original static Az/B/H at magnetic-domain [x_m,y_m] points with one-sided region metadata')
    planar_bh_probe.add_argument('run',type=Path);planar_bh_probe.add_argument('--points',required=True,type=Path)
    planar_bh_probe.add_argument('--out',required=True,type=Path)
    axis_bh=sub.add_parser('solve-axis-bh',help='solve an explicit axis nonlinear B-H/current a=Aphi/r case with verified success or retained failure output')
    axis_bh.add_argument('case',type=Path);axis_bh.add_argument('--out',required=True,type=Path)
    axis_bh_replay=sub.add_parser('replay-axis-bh',help='reconstruct B-H curves, Newton histories, signed currents, a/Ht/axis boundaries, a/Aphi/B/H and all integral quantities')
    axis_bh_replay.add_argument('run',type=Path)
    axis_bh_probe=sub.add_parser('probe-axis-bh',help='export original static a/Aphi/B/H at magnetic-domain [r_m,z_m] points with one-sided region metadata')
    axis_bh_probe.add_argument('run',type=Path);axis_bh_probe.add_argument('--points',required=True,type=Path)
    axis_bh_probe.add_argument('--out',required=True,type=Path)
    off_axis_bh=sub.add_parser('solve-off-axis-bh',help='solve an explicit off-axis nonlinear B-H/current psi=r*Aphi case with verified success or retained failure output')
    off_axis_bh.add_argument('case',type=Path);off_axis_bh.add_argument('--out',required=True,type=Path)
    off_axis_bh_replay=sub.add_parser('replay-off-axis-bh',help='reconstruct B-H curves, Newton histories, signed currents, psi/Ht boundaries, psi/Aphi/B/H and all integral quantities')
    off_axis_bh_replay.add_argument('run',type=Path)
    off_axis_bh_probe=sub.add_parser('probe-off-axis-bh',help='export original static psi/Aphi/B/H at magnetic-domain [r_m,z_m] points with one-sided region metadata')
    off_axis_bh_probe.add_argument('run',type=Path);off_axis_bh_probe.add_argument('--points',required=True,type=Path)
    off_axis_bh_probe.add_argument('--out',required=True,type=Path)
    off_axis_magnetostatic=sub.add_parser('solve-off-axis-magnetostatic',help='solve an explicit positive-radius magnetic/current psi case with verified native output')
    off_axis_magnetostatic.add_argument('case',type=Path);off_axis_magnetostatic.add_argument('--out',required=True,type=Path)
    off_axis_magnetostatic_replay=sub.add_parser('replay-off-axis-magnetostatic',help='reconstruct magnetic materials, signed currents, psi/Ht boundaries, psi/Aphi/B/H and all integral quantities')
    off_axis_magnetostatic_replay.add_argument('run',type=Path)
    off_axis_magnetostatic_probe=sub.add_parser('probe-off-axis-magnetostatic',help='export original static psi/Aphi/B/H at magnetic-domain [r_m,z_m] points with one-sided region metadata')
    off_axis_magnetostatic_probe.add_argument('run',type=Path);off_axis_magnetostatic_probe.add_argument('--points',required=True,type=Path)
    off_axis_magnetostatic_probe.add_argument('--out',required=True,type=Path)
    off_axis_recoil=sub.add_parser('solve-off-axis-recoil',help='solve an explicit positive-radius recoil tensor/remanence/current psi case with verified native output')
    off_axis_recoil.add_argument('case',type=Path);off_axis_recoil.add_argument('--out',required=True,type=Path)
    off_axis_recoil_replay=sub.add_parser('replay-off-axis-recoil',help='reconstruct recoil tensors, remanent induction, signed currents, psi/Ht boundaries, psi/Aphi/B/H and all integral quantities')
    off_axis_recoil_replay.add_argument('run',type=Path)
    off_axis_recoil_probe=sub.add_parser('probe-off-axis-recoil',help='export original static psi/Aphi/B/H at magnetic-domain [r_m,z_m] points with one-sided region metadata')
    off_axis_recoil_probe.add_argument('run',type=Path);off_axis_recoil_probe.add_argument('--points',required=True,type=Path)
    off_axis_recoil_probe.add_argument('--out',required=True,type=Path)
    axis_magnetostatic=sub.add_parser('solve-axis-magnetostatic',help='solve an explicit axis-connected magnetic/current Aphi case with verified native output')
    axis_magnetostatic.add_argument('case',type=Path);axis_magnetostatic.add_argument('--out',required=True,type=Path)
    axis_magnetostatic_replay=sub.add_parser('replay-axis-magnetostatic',help='reconstruct magnetic materials, signed currents, axis/fixed Aphi/r/Ht boundaries, Aphi/B/H and all integral quantities')
    axis_magnetostatic_replay.add_argument('run',type=Path)
    axis_magnetostatic_probe=sub.add_parser('probe-axis-magnetostatic',help='export original static Aphi/B/H at magnetic-domain [r_m,z_m] points with one-sided region metadata')
    axis_magnetostatic_probe.add_argument('run',type=Path);axis_magnetostatic_probe.add_argument('--points',required=True,type=Path)
    axis_magnetostatic_probe.add_argument('--out',required=True,type=Path)
    axis_recoil=sub.add_parser('solve-axis-recoil',help='solve an explicit axis-connected recoil tensor/remanence/current Aphi case with verified native output')
    axis_recoil.add_argument('case',type=Path);axis_recoil.add_argument('--out',required=True,type=Path)
    axis_recoil_replay=sub.add_parser('replay-axis-recoil',help='reconstruct recoil tensors, remanent induction, signed currents, axis/fixed Aphi/r/Ht boundaries, Aphi/B/H and all integral quantities')
    axis_recoil_replay.add_argument('run',type=Path)
    axis_recoil_probe=sub.add_parser('probe-axis-recoil',help='export original static Aphi/B/H at magnetic-domain [r_m,z_m] points with one-sided region metadata')
    axis_recoil_probe.add_argument('run',type=Path);axis_recoil_probe.add_argument('--points',required=True,type=Path)
    axis_recoil_probe.add_argument('--out',required=True,type=Path)
    material_hphi=sub.add_parser('solve-material-hphi',help='solve an explicit piecewise lossless material Hphi case with verified native output')
    material_hphi.add_argument('case',type=Path);material_hphi.add_argument('--out',required=True,type=Path)
    material_hphi_replay=sub.add_parser('replay-material-hphi',help='reconstruct materials and geometry, lowest positive FEM and all RF, and emit verified JSON')
    material_hphi_replay.add_argument('run',type=Path)
    material_hphi_probe=sub.add_parser('probe-material-hphi',help='export original signed E/H/B fields at material [r_m,z_m] points with one-sided region metadata')
    material_hphi_probe.add_argument('run',type=Path);material_hphi_probe.add_argument('--points',required=True,type=Path)
    material_hphi_probe.add_argument('--mode',type=int,default=1,help='one-based positive-spectrum rank, not a mode identity')
    material_hphi_probe.add_argument('--out',required=True,type=Path)
    hphi=sub.add_parser('solve-axis-hphi',help='solve explicit axis-connected vacuum Hphi mesh, including PEC holes')
    hphi.add_argument('case',type=Path)
    hphi.add_argument('--out',required=True,type=Path)
    hphi_replay=sub.add_parser('replay-axis-hphi',help='verify Hphi mesh topology, regular positive spectrum and all wall losses')
    hphi_replay.add_argument('run',type=Path)
    hphi_probe=sub.add_parser('probe-axis-hphi',help='export signed E/H/B at vacuum [r_m,z_m] points; reject conductor interiors')
    hphi_probe.add_argument('run',type=Path)
    hphi_probe.add_argument('--points',type=Path,required=True)
    hphi_probe.add_argument('--mode',type=int,default=1,help='one-based positive-spectrum index, not a tracked mode identity')
    hphi_probe.add_argument('--out',type=Path,required=True)
    hphi=sub.add_parser('solve-hphi-mesh',help='solve explicit positive-radius vacuum Hphi mesh, including PEC holes')
    hphi.add_argument('case',type=Path)
    hphi.add_argument('--out',required=True,type=Path)
    hphi_replay=sub.add_parser('replay-hphi-mesh',help='verify Hphi mesh topology, positive spectrum and all wall losses')
    hphi_replay.add_argument('run',type=Path)
    hphi_probe=sub.add_parser('probe-hphi-mesh',help='export signed E/H/B at vacuum [r_m,z_m] points; reject conductor interiors')
    hphi_probe.add_argument('run',type=Path)
    hphi_probe.add_argument('--points',type=Path,required=True)
    hphi_probe.add_argument('--mode',type=int,default=1,help='one-based positive-spectrum index, not a tracked mode identity')
    hphi_probe.add_argument('--out',type=Path,required=True)
    coaxial=sub.add_parser('solve-coaxial',help='solve a closed vacuum coaxial m=0 Hphi case; exclude static circulation')
    coaxial.add_argument('case',type=Path)
    coaxial.add_argument('--out',required=True,type=Path)
    coaxial_replay=sub.add_parser('replay-coaxial',help='reassemble and verify coaxial native fields, positive spectrum and full-cavity RF')
    coaxial_replay.add_argument('run',type=Path)
    coaxial_probe=sub.add_parser('probe-coaxial',help='export signed E/H/B at declared vacuum [r_m,z_m] points to new JSON')
    coaxial_probe.add_argument('run',type=Path)
    coaxial_probe.add_argument('--points',type=Path,required=True)
    coaxial_probe.add_argument('--mode',type=int,default=1,help='one-based positive-spectrum index, not a TEM/TM label')
    coaxial_probe.add_argument('--out',type=Path,required=True)
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
    static_solve = sub.add_parser('solve-static-project', help='solve a dedicated static Project with verified native success or retained nonlinear failure')
    static_solve.add_argument('input', type=Path)
    static_solve.add_argument('--out', type=Path, required=True)
    static_replay = sub.add_parser('replay-static-project', help='recompute a saved static Project outcome with its original dedicated FEM')
    static_replay.add_argument('run', type=Path)
    static_project = sub.add_parser('normalize-static-project', help='validate a dedicated static Case/Project and publish a portable Project without solving or changing SI values')
    static_project.add_argument('input', type=Path)
    static_project.add_argument('--out', type=Path, required=True)
    static_project.add_argument('--display-length-unit', choices=('m', 'mm'))
    static_study = sub.add_parser('normalize-static-study', help='validate every independent static Study point and publish the input without solving')
    static_study.add_argument('input', type=Path)
    static_study.add_argument('--out', type=Path, required=True)
    static_study_solve = sub.add_parser('solve-static-study', help='execute every independent static Study point, retaining actual nonlinear failures')
    static_study_solve.add_argument('input', type=Path)
    static_study_solve.add_argument('--out', type=Path, required=True)
    static_study_replay = sub.add_parser('replay-static-study', help='rebuild and replay every saved static Study point and outcome')
    static_study_replay.add_argument('run', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command in ('solve-static-study', 'replay-static-study'):
            from .static_field_study import StaticFieldStudy
            from .static_field_study_jobs import execute_static_field_study, read_static_field_study
            result = (execute_static_field_study(StaticFieldStudy.load(args.input), args.out)
                      if args.command == 'solve-static-study' else read_static_field_study(args.run))
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return 0 if result['all_points_successful'] else 1
        if args.command == 'normalize-static-study':
            from .static_field_study import StaticFieldStudy
            study = StaticFieldStudy.load(args.input)
            study.save(args.out)
            sys.stdout.write(study.dumps())
            return 0
        if args.command in ('solve-static-project', 'replay-static-project'):
            from .static_field_project import StaticFieldProject
            from .static_field_jobs import execute_static_field_project, read_static_field_job
            result = (execute_static_field_project(StaticFieldProject.load(args.input), args.out)
                      if args.command == 'solve-static-project' else read_static_field_job(args.run))
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return 1 if result['status'] == 'nonlinear_failed' else 0
        if args.command == 'normalize-static-project':
            from .static_field_project import StaticFieldProject
            project = StaticFieldProject.load(args.input)
            if args.display_length_unit is not None:
                project = replace(project, display_length_unit=args.display_length_unit)
            project.save(args.out)
            sys.stdout.write(project.dumps())
            return 0
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
        if args.command in ('execute-hphi-history','extend-hphi-history','replay-hphi-history'):
            from .hphi_tracking_history import HphiTrackingHistoryRequest
            from .hphi_tracking_history_saved import execute_hphi_history,extend_hphi_history,read_hphi_history
            if args.command=='execute-hphi-history':
                result=execute_hphi_history(args.steps,HphiTrackingHistoryRequest.load(args.request),args.out)
            elif args.command=='extend-hphi-history':
                result=extend_hphi_history(args.history,args.next_pair,args.out)
            else:
                result=read_hphi_history(args.run)
            print(json.dumps(result,indent=2,allow_nan=False));return 0
        if args.command in ('execute-hphi-tracking','replay-hphi-tracking'):
            from .hphi_tracking import HphiTrackingRequest
            from .hphi_tracking_jobs import execute_hphi_tracking,read_hphi_tracking
            result=(execute_hphi_tracking(args.previous,args.current,HphiTrackingRequest.load(args.request),args.out)
                    if args.command=='execute-hphi-tracking' else read_hphi_tracking(args.run))
            print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False));return 0
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
        if args.command in ('execute-hphi-convergence','replay-hphi-convergence'):
            from .hphi_convergence import HphiConvergence
            from .hphi_convergence_saved import execute_hphi_convergence,read_hphi_convergence
            result=execute_hphi_convergence(HphiConvergence.load(args.request),args.out) if args.command=='execute-hphi-convergence' else read_hphi_convergence(args.run)
            print(json.dumps(result,indent=2,allow_nan=False))
            return 0
        if args.command in ('execute-hphi-study','replay-hphi-study'):
            from .hphi_study import HphiStudy
            from .hphi_study_jobs import execute_hphi_study, read_hphi_study
            result=(execute_hphi_study(HphiStudy.load(args.study),args.out) if args.command=='execute-hphi-study' else read_hphi_study(args.run))
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
        if args.command in ('plot-hphi','probe-hphi-csv'):
            from .hphi_display import plot_hphi_mode,export_hphi_probe
            if args.command=='plot-hphi':
                plot_hphi_mode(args.run,args.out,args.mode,mesh=args.mesh,length_unit=args.length_unit)
            else:
                from .project import parse_json
                export_hphi_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')),args.mode)
            print(f'WROTE: {args.out}')
            return 0
        if args.command=='execute-hphi-project':
            from .hphi_project import HphiProject
            from .hphi_jobs import execute_hphi_project
            print(json.dumps(execute_hphi_project(HphiProject.load(args.project),args.out),indent=2,allow_nan=False))
            return 0
        if args.command in ('solve-curved-hphi','replay-curved-hphi','probe-curved-hphi'):
            from .curved_hphi import CurvedHphiCase,solve_curved_hphi
            from .curved_hphi_saved import save_curved_hphi_run,read_curved_hphi_run,curved_hphi_result,export_curved_hphi_probe
            if args.command=='solve-curved-hphi':
                case=CurvedHphiCase.load(args.case)
                print(json.dumps(save_curved_hphi_run(case,solve_curved_hphi(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-curved-hphi':
                print(json.dumps(curved_hphi_result(read_curved_hphi_run(args.run)),indent=2,allow_nan=False))
            else:
                from .project import parse_json
                export_curved_hphi_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')),args.mode)
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-electrostatic','replay-electrostatic','probe-electrostatic'):
            from .electrostatic import AxisymmetricElectrostaticCase,solve_axisymmetric_electrostatic
            from .electrostatic_saved import save_electrostatic_run,read_electrostatic_run,electrostatic_result,export_electrostatic_probe
            from .project import parse_json
            if args.command=='solve-electrostatic':
                case=AxisymmetricElectrostaticCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                print(json.dumps(save_electrostatic_run(case,solve_axisymmetric_electrostatic(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-electrostatic':
                print(json.dumps(electrostatic_result(read_electrostatic_run(args.run)),indent=2,allow_nan=False))
            else:
                export_electrostatic_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-planar-electrostatic','replay-planar-electrostatic','probe-planar-electrostatic'):
            from .planar_electrostatic import PlanarElectrostaticCase,solve_planar_electrostatic
            from .planar_electrostatic_saved import save_planar_electrostatic_run,read_planar_electrostatic_run,planar_electrostatic_result,export_planar_electrostatic_probe
            from .project import parse_json
            if args.command=='solve-planar-electrostatic':
                case=PlanarElectrostaticCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                print(json.dumps(save_planar_electrostatic_run(case,solve_planar_electrostatic(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-planar-electrostatic':
                print(json.dumps(planar_electrostatic_result(read_planar_electrostatic_run(args.run)),indent=2,allow_nan=False))
            else:
                export_planar_electrostatic_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('analyze-off-axis-magnetic-force','replay-off-axis-magnetic-force'):
            from .off_axis_magnetic_force_saved import export_off_axis_magnetic_force,replay_off_axis_magnetic_force
            from .project import parse_json
            if args.command=='analyze-off-axis-magnetic-force':result=export_off_axis_magnetic_force(args.run,args.out,parse_json(args.request.read_text(encoding='utf-8')))
            else:result=replay_off_axis_magnetic_force(args.run,args.report)
            print(json.dumps(result,indent=2,allow_nan=False));return 0
        if args.command in ('analyze-planar-magnetic-force','replay-planar-magnetic-force'):
            from .planar_magnetic_force_saved import export_planar_magnetic_force,replay_planar_magnetic_force
            from .project import parse_json
            if args.command=='analyze-planar-magnetic-force':result=export_planar_magnetic_force(args.run,args.out,parse_json(args.request.read_text(encoding='utf-8')))
            else:result=replay_planar_magnetic_force(args.run,args.report)
            print(json.dumps(result,indent=2,allow_nan=False))
            return 1 if result.get('status')=='virtual_work_failed' else 0
        if args.command in ('extract-planar-magnetic-multipoles','replay-planar-magnetic-multipoles'):
            from .planar_magnetic_multipole_saved import export_planar_magnetic_multipoles,replay_planar_magnetic_multipoles
            from .project import parse_json
            if args.command=='extract-planar-magnetic-multipoles':
                result=export_planar_magnetic_multipoles(args.run,args.out,parse_json(args.request.read_text(encoding='utf-8')))
            else:result=replay_planar_magnetic_multipoles(args.run,args.report)
            print(json.dumps(result,indent=2,allow_nan=False))
            return 0
        if args.command in ('solve-planar-magnetostatic','replay-planar-magnetostatic','probe-planar-magnetostatic'):
            from .planar_magnetostatic import PlanarMagnetostaticCase,solve_planar_magnetostatic
            from .planar_magnetostatic_saved import save_planar_magnetostatic_run,read_planar_magnetostatic_run,planar_magnetostatic_result,export_planar_magnetostatic_probe
            from .project import parse_json
            if args.command=='solve-planar-magnetostatic':
                case=PlanarMagnetostaticCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                print(json.dumps(save_planar_magnetostatic_run(case,solve_planar_magnetostatic(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-planar-magnetostatic':
                print(json.dumps(planar_magnetostatic_result(read_planar_magnetostatic_run(args.run)),indent=2,allow_nan=False))
            else:
                export_planar_magnetostatic_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-planar-recoil','replay-planar-recoil','probe-planar-recoil'):
            from .planar_recoil import PlanarRecoilCase,solve_planar_recoil
            from .planar_recoil_saved import save_planar_recoil_run,read_planar_recoil_run,planar_recoil_result,export_planar_recoil_probe
            from .project import parse_json
            if args.command=='solve-planar-recoil':
                case=PlanarRecoilCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                print(json.dumps(save_planar_recoil_run(case,solve_planar_recoil(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-planar-recoil':
                print(json.dumps(planar_recoil_result(read_planar_recoil_run(args.run)),indent=2,allow_nan=False))
            else:
                export_planar_recoil_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-planar-bh','replay-planar-bh','probe-planar-bh'):
            from .planar_bh import PlanarBHCase,solve_planar_bh
            from .nonlinear_magnetic import MagneticNonlinearFailure
            from .planar_bh_saved import save_planar_bh_run,read_planar_bh_run,planar_bh_result,export_planar_bh_probe,save_planar_bh_failure,read_planar_bh_outcome
            from .project import parse_json
            if args.command=='solve-planar-bh':
                case=PlanarBHCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                try:solution=solve_planar_bh(case)
                except MagneticNonlinearFailure as exc:
                    print(json.dumps(save_planar_bh_failure(case,exc,args.out),indent=2,allow_nan=False))
                    return 1
                print(json.dumps(save_planar_bh_run(case,solution,args.out),indent=2,allow_nan=False))
            elif args.command=='replay-planar-bh':
                result=read_planar_bh_outcome(args.run)
                print(json.dumps(result,indent=2,allow_nan=False))
                return 1 if result['status']=='failed' else 0
            else:
                export_planar_bh_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-axis-bh','replay-axis-bh','probe-axis-bh'):
            from .axis_bh import AxisBHCase,solve_axis_bh
            from .nonlinear_magnetic import MagneticNonlinearFailure
            from .axis_bh_saved import save_axis_bh_run,read_axis_bh_run,axis_bh_result,export_axis_bh_probe,save_axis_bh_failure,read_axis_bh_outcome
            from .project import parse_json
            if args.command=='solve-axis-bh':
                case=AxisBHCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                try:solution=solve_axis_bh(case)
                except MagneticNonlinearFailure as exc:
                    print(json.dumps(save_axis_bh_failure(case,exc,args.out),indent=2,allow_nan=False))
                    return 1
                print(json.dumps(save_axis_bh_run(case,solution,args.out),indent=2,allow_nan=False))
            elif args.command=='replay-axis-bh':
                result=read_axis_bh_outcome(args.run)
                print(json.dumps(result,indent=2,allow_nan=False))
                return 1 if result['status']=='failed' else 0
            else:
                export_axis_bh_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-off-axis-bh','replay-off-axis-bh','probe-off-axis-bh'):
            from .off_axis_bh import OffAxisBHCase,solve_off_axis_bh
            from .nonlinear_magnetic import MagneticNonlinearFailure
            from .off_axis_bh_saved import save_off_axis_bh_run,read_off_axis_bh_run,off_axis_bh_result,export_off_axis_bh_probe,save_off_axis_bh_failure,read_off_axis_bh_outcome
            from .project import parse_json
            if args.command=='solve-off-axis-bh':
                case=OffAxisBHCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                try:solution=solve_off_axis_bh(case)
                except MagneticNonlinearFailure as exc:
                    print(json.dumps(save_off_axis_bh_failure(case,exc,args.out),indent=2,allow_nan=False))
                    return 1
                print(json.dumps(save_off_axis_bh_run(case,solution,args.out),indent=2,allow_nan=False))
            elif args.command=='replay-off-axis-bh':
                result=read_off_axis_bh_outcome(args.run)
                print(json.dumps(result,indent=2,allow_nan=False))
                return 1 if result['status']=='failed' else 0
            else:
                export_off_axis_bh_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-off-axis-magnetostatic','replay-off-axis-magnetostatic','probe-off-axis-magnetostatic'):
            from .off_axis_magnetostatic import OffAxisMagnetostaticCase,solve_off_axis_magnetostatic
            from .off_axis_magnetostatic_saved import save_off_axis_magnetostatic_run,read_off_axis_magnetostatic_run,off_axis_magnetostatic_result,export_off_axis_magnetostatic_probe
            from .project import parse_json
            if args.command=='solve-off-axis-magnetostatic':
                case=OffAxisMagnetostaticCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                print(json.dumps(save_off_axis_magnetostatic_run(case,solve_off_axis_magnetostatic(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-off-axis-magnetostatic':
                print(json.dumps(off_axis_magnetostatic_result(read_off_axis_magnetostatic_run(args.run)),indent=2,allow_nan=False))
            else:
                export_off_axis_magnetostatic_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-off-axis-recoil','replay-off-axis-recoil','probe-off-axis-recoil'):
            from .off_axis_recoil import OffAxisRecoilCase,solve_off_axis_recoil
            from .off_axis_recoil_saved import save_off_axis_recoil_run,read_off_axis_recoil_run,off_axis_recoil_result,export_off_axis_recoil_probe
            from .project import parse_json
            if args.command=='solve-off-axis-recoil':
                case=OffAxisRecoilCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                print(json.dumps(save_off_axis_recoil_run(case,solve_off_axis_recoil(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-off-axis-recoil':
                print(json.dumps(off_axis_recoil_result(read_off_axis_recoil_run(args.run)),indent=2,allow_nan=False))
            else:
                export_off_axis_recoil_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-axis-magnetostatic','replay-axis-magnetostatic','probe-axis-magnetostatic'):
            from .axis_magnetostatic import AxisMagnetostaticCase,solve_axis_magnetostatic
            from .axis_magnetostatic_saved import save_axis_magnetostatic_run,read_axis_magnetostatic_run,axis_magnetostatic_result,export_axis_magnetostatic_probe
            from .project import parse_json
            if args.command=='solve-axis-magnetostatic':
                case=AxisMagnetostaticCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                print(json.dumps(save_axis_magnetostatic_run(case,solve_axis_magnetostatic(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-axis-magnetostatic':
                print(json.dumps(axis_magnetostatic_result(read_axis_magnetostatic_run(args.run)),indent=2,allow_nan=False))
            else:
                export_axis_magnetostatic_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-axis-recoil','replay-axis-recoil','probe-axis-recoil'):
            from .axis_recoil import AxisRecoilCase,solve_axis_recoil
            from .axis_recoil_saved import save_axis_recoil_run,read_axis_recoil_run,axis_recoil_result,export_axis_recoil_probe
            from .project import parse_json
            if args.command=='solve-axis-recoil':
                case=AxisRecoilCase.from_dict(parse_json(args.case.read_text(encoding='utf-8')))
                print(json.dumps(save_axis_recoil_run(case,solve_axis_recoil(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-axis-recoil':
                print(json.dumps(axis_recoil_result(read_axis_recoil_run(args.run)),indent=2,allow_nan=False))
            else:
                export_axis_recoil_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')))
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-material-hphi','replay-material-hphi','probe-material-hphi'):
            from .material_hphi import MaterialHphiCase,solve_material_hphi
            from .material_hphi_saved import save_material_hphi_run,read_material_hphi_run,material_hphi_result,export_material_hphi_probe
            if args.command=='solve-material-hphi':
                case=MaterialHphiCase.load(args.case)
                print(json.dumps(save_material_hphi_run(case,solve_material_hphi(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-material-hphi':
                print(json.dumps(material_hphi_result(read_material_hphi_run(args.run)),indent=2,allow_nan=False))
            else:
                from .project import parse_json
                export_material_hphi_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')),args.mode)
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-axis-hphi','replay-axis-hphi','probe-axis-hphi'):
            from .axis_hphi import AxisHphiCase,solve_axis_hphi
            from .axis_hphi_saved import save_axis_hphi_run,read_axis_hphi_run,export_axis_hphi_probe
            if args.command=='solve-axis-hphi':
                case=AxisHphiCase.load(args.case)
                print(json.dumps(save_axis_hphi_run(case,solve_axis_hphi(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-axis-hphi':
                read_axis_hphi_run(args.run)
                print(f'PASS: {args.run} (axis-connected Hphi mesh; regular axis; all PEC components; energy J; loss W)')
            else:
                from .project import parse_json
                export_axis_hphi_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')),args.mode)
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-hphi-mesh','replay-hphi-mesh','probe-hphi-mesh'):
            from .hphi_mesh import HphiMeshCase,solve_hphi_mesh
            from .hphi_mesh_saved import save_hphi_mesh_run,read_hphi_mesh_run,export_hphi_mesh_probe
            if args.command=='solve-hphi-mesh':
                case=HphiMeshCase.load(args.case)
                print(json.dumps(save_hphi_mesh_run(case,solve_hphi_mesh(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-hphi-mesh':
                read_hphi_mesh_run(args.run)
                print(f'PASS: {args.run} (positive-radius Hphi mesh; all PEC components; energy J; loss W)')
            else:
                from .project import parse_json
                export_hphi_mesh_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')),args.mode)
                print(f'WROTE: {args.out}')
            return 0
        if args.command in ('solve-coaxial','replay-coaxial','probe-coaxial'):
            from .coaxial import CoaxialCase,solve_coaxial
            from .coaxial_saved import save_coaxial_run,read_coaxial_run,export_coaxial_probe
            if args.command=='solve-coaxial':
                case=CoaxialCase.load(args.case)
                print(json.dumps(save_coaxial_run(case,solve_coaxial(case),args.out),indent=2,allow_nan=False))
            elif args.command=='replay-coaxial':
                read_coaxial_run(args.run)
                print(f'PASS: {args.run} (closed coaxial Hphi; static circulation excluded; energy J; loss W)')
            else:
                from .project import parse_json
                export_coaxial_probe(args.run,args.out,parse_json(args.points.read_text(encoding='utf-8')),args.mode)
                print(f'WROTE: {args.out}')
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
        elif args.command == 'freeze-curved-refinement':
            from .frozen_curved_refinement import freeze_curved_refinement
            from .project import load_document
            result=freeze_curved_refinement(load_document(args.project.read_text(encoding='utf-8')))
            with args.out.open('x',encoding='utf-8') as stream:
                json.dump(result.to_dict(),stream,indent=2,allow_nan=False);stream.write('\n')
            print(f"FROZEN: {args.out}")
            return 0
        elif args.command == 'deform-curved-project':
            from .curved_harmonic_deformation import deform_curved_project
            from .project import load_document,parse_json
            result=deform_curved_project(load_document(args.project.read_text(encoding='utf-8')),
                parse_json(args.geometry.read_text(encoding='utf-8')),rf_coordinates=args.rf_coordinates,
                minimum_corner_angle_deg=args.minimum_corner_angle_deg)
            with args.out.open('x',encoding='utf-8') as stream:
                json.dump(result.to_dict(),stream,indent=2,allow_nan=False);stream.write('\n')
            print(f"DEFORMED: {args.out}")
            return 0
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
