# SPDX-License-Identifier: Apache-2.0
"""Full-field RF-goal journal reconstruction; no eigenproblem or file writes.

Historical timings are checked and retained, never remeasured into the original
record. Source aliases identify exact original bytes and are never executed.
"""
from copy import deepcopy
import math
from pathlib import Path, PurePosixPath

import numpy as np

from . import curved_adaptive_refinement as curved
from . import curved_rf_adaptive_refinement as native
from .adaptive_efficiency_domain import _native_files, verify_efficiency_saved_domain
from .adaptive_efficiency_reference import _bound_file, verify_reference_bytes
from .adaptive_efficiency_timing import PhaseRecorder
from .adaptive_efficiency_worker import _uniform_plan
from .completion import digest
from .config import Case, integer, keys
from .curved_rf_goal_efficiency_metrics import assess_rf_goal_history
from .curved_rf_goal_efficiency_plan import request_for_curved_rf_goal_efficiency_execution, _same
from .curved_rf_goal_efficiency_reference import load_curved_rf_goal_efficiency_reference
from .curved_rf_goal_efficiency_worker import _sample_event, _uniform_event, _stop_status, _verify_fixed_request, observation_bindings
from .geometry_surface_numerics import mapped_moments
from .jobs import _implementation_hashes
from .mesh_input import mesh_digest
from .project import parse_json
from .saved_mode_tracking import _canonical


_REQUIRED=('schema_version','document_type','execution','request','status','native_status','public_checkpoint','events',
           'level_runs','native_sources','event_records','observations','assessment','reference_bound_inputs',
           'implementation_sha256','native_solves_attempted','native_solves_completed','physical_error_bound',
           'development_event_limit','scope')
_SCOPE='fresh fixed RF-goal native branch and full-grid finite metrics; public checkpoint frozen before benchmark continuation; full journal replay/resume remains required'


def _same_saved(value, expected, location):
    # Runtime numpy float scalars and tuples use the producer's exact JSON
    # representation. Caller types stay strict; no numerical tolerance/fit.
    _same(value,parse_json(_canonical(expected)),location)


def _number(value, name):
    if type(value) not in (float,int) or not math.isfinite(value) or value<0:
        raise ValueError(name+' requires a finite nonnegative historical measurement')
    return value


def _close(a,b):
    return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)


def _verify_costs(document):
    """Verify stored arithmetic/ordering; historical elapsed time is not rerun."""
    if any(type(r) is not dict or type(r.get('observed_prefix_cost')) is not dict for r in document['event_records']):
        raise ValueError('RF event lacks its original observed prefix cost')
    prefixes=[r['observed_prefix_cost'] for r in document['event_records']]
    for i,p in enumerate(prefixes):
        names=('native_path_cumulative_seconds','recorder_prefix_wall_seconds','submission_prefix_wall_seconds','scope')
        keys(p,names,names,'historical RF prefix cost')
        for k in ('native_path_cumulative_seconds','recorder_prefix_wall_seconds'):_number(p[k],k)
        if p['submission_prefix_wall_seconds'] is not None:
            _number(p['submission_prefix_wall_seconds'],'submission prefix')
            if p['submission_prefix_wall_seconds']<p['recorder_prefix_wall_seconds']:
                raise ValueError('historical submission clock starts before the recorder and cannot cover less time')
        if p['native_path_cumulative_seconds']>p['recorder_prefix_wall_seconds']:
            raise ValueError('historical native prefix exceeds recorder wall')
        if i and any(p[k]<prefixes[i-1][k] for k in ('native_path_cumulative_seconds','recorder_prefix_wall_seconds')):
            raise ValueError('historical RF prefixes moved backwards')
        if i and (p['submission_prefix_wall_seconds'] is None)!=(prefixes[i-1]['submission_prefix_wall_seconds'] is None):
            raise ValueError('historical submission clock coverage changed between prefixes')
        if i and p['submission_prefix_wall_seconds'] is not None and p['submission_prefix_wall_seconds']<prefixes[i-1]['submission_prefix_wall_seconds']:
            raise ValueError('historical submission prefix moved backwards')
    if 'observed_cost' not in document:return 'PREFIX_ONLY_NOT_REMEASURED'
    cost=document['observed_cost']
    fields=('schema_version','document_type','status','wall_seconds','recorded_phase_seconds','unattributed_seconds',
            'phases','timing_errors','peak_rss_bytes','memory_status','memory_reason','scope')
    keys(cost,fields,fields,'historical RF observed cost')
    phases=cost['phases']
    if type(cost['schema_version']) is not int or cost['schema_version']!=1 or cost['document_type']!='adaptive_efficiency_observed_cost':
        raise ValueError('historical RF observed cost schema differs')
    if cost.get('status')!='COMPLETE' or type(phases) is not list or cost.get('timing_errors')!=[]:
        raise ValueError('completed RF journal requires complete finite original phase records')
    if cost['memory_status']=='RECORDED':
        if type(cost['peak_rss_bytes']) is not int or cost['peak_rss_bytes']<=0 or cost['memory_reason'] is not None:
            raise ValueError('recorded historical RSS requires positive integer bytes and no unknown reason')
    elif cost['memory_status']=='UNKNOWN':
        if cost['peak_rss_bytes'] is not None or type(cost['memory_reason']) is not str or not cost['memory_reason']:
            raise ValueError('unknown historical RSS requires null bytes and its actual reason')
    else:raise ValueError('historical RSS status must remain RECORDED or UNKNOWN')
    for i,p in enumerate(phases):
        fields=('index','name','parent_index','status','exception_type','inclusive_seconds','exclusive_seconds')
        keys(p,fields,fields,'historical RF phase')
        if type(p['name']) is not str or not p['name']:raise ValueError('historical RF phase requires its actual name')
        if type(p['index']) is not int or p['index']!=i or p['status']!='COMPLETED' or p['exception_type'] is not None:
            raise ValueError('historical phase indices/status differ')
        parent=p['parent_index']
        if parent is not None and (type(parent) is not int or not 0<=parent<i):
            raise ValueError('historical phase parent must precede its child')
        for k in ('inclusive_seconds','exclusive_seconds'):_number(p[k],k)
    # A completed subtree cannot be re-entered later in chronological order.
    stack=[];closed=set()
    for i,p in enumerate(phases):
        parent=p['parent_index']
        while stack and stack[-1]!=parent:closed.add(stack.pop())
        if parent is not None and (not stack or parent in closed):
            raise ValueError('historical phase nesting is not contiguous')
        stack.append(i)
    for i,p in enumerate(phases):
        children=math.fsum(q['inclusive_seconds'] for q in phases if q['parent_index']==i)
        if not _close(p['inclusive_seconds']-children,p['exclusive_seconds']):
            raise ValueError('historical exclusive phase cost differs from inclusive minus children')
    roots=[(i,p) for i,p in enumerate(phases) if p['parent_index'] is None]
    if document.get('observation_schema_version',1)==2:
        factors=[p for p in phases if p['name']=='adjoint_factorization']
        solves=[p for p in phases if p['name']=='adjoint_linear_solve']
        if len(factors)!=len(solves) or any(a['index']>=b['index'] or a['parent_index']!=b['parent_index'] for a,b in zip(factors,solves)):
            raise ValueError('RF observation version 2 requires each actual adjoint factorization and following C solve in the same parent')
    for k in ('wall_seconds','recorded_phase_seconds','unattributed_seconds'):_number(cost[k],k)
    total=math.fsum(p['inclusive_seconds'] for _,p in roots)
    if (not _close(total,cost['recorded_phase_seconds']) or
            not _close(cost['wall_seconds'],total+cost['unattributed_seconds'])):
        raise ValueError('historical root phases or total wall are inconsistent')
    cutoffs=[i for i,p in roots if p['name']=='independent_accuracy_and_parent_changes']
    if len(cutoffs)!=len(prefixes) or sum(p['name']=='native_event' for _,p in roots)!=len(prefixes):
        raise ValueError('historical event/accuracy phase coverage differs from all saved events')
    names={'initial_plan','native_event','next_uniform_plan','complete_public_replay'}
    for prefix,end in zip(prefixes,cutoffs):
        measured=math.fsum(p['inclusive_seconds'] for i,p in roots if i<=end and p['name'] in names)
        elapsed=math.fsum(p['inclusive_seconds'] for i,p in roots if i<=end)
        if (not _close(measured,prefix['native_path_cumulative_seconds']) or
                prefix['recorder_prefix_wall_seconds']+1e-12<elapsed or prefix['recorder_prefix_wall_seconds']>cost['wall_seconds']):
            raise ValueError('historical event prefix omits or changes observed work')
    return 'STRUCTURE_VERIFIED_NOT_REMEASURED'


def _implementation_sources(sources, aliases=None, archives=None):
    if type(sources) is not dict or not sources:
        raise ValueError('RF journal requires its declared original implementation SHA256 map')
    required={'solver.py','curved_solution.py','curved_rf.py','curved_rf_adaptive_refinement.py',
              'curved_rf_goal_efficiency_worker.py','curved_rf_goal_efficiency_metrics.py',
              'curved_rf_goal_efficiency_plan.py','curved_rf_goal_efficiency_reference.py','adaptive_efficiency_fields.py'}
    if not required<=set(sources):raise ValueError('RF journal lacks required original solver/comparison source bindings')
    aliases={} if aliases is None else aliases
    if type(aliases) is not dict or not set(aliases)<=set(sources):
        raise ValueError('implementation aliases must name only declared original sources')
    root=Path(__file__).parent;bound={};archives={} if archives is None else archives
    if type(archives) is not dict:raise ValueError('implementation archives require a SHA256-to-absolute-path mapping')
    for sha,path in archives.items():
        if (type(sha) is not str or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha) or
                type(path) is not str or not Path(path).is_absolute()):
            raise ValueError('implementation archives require exact SHA256 keys and absolute paths')
        _bound_file(path,sha,bound)
    for name,sha in sources.items():
        if (type(name) is not str or not name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or
                PurePosixPath(name).as_posix()!=name or '\\' in name):
            raise ValueError('implementation source requires an original package-relative path')
        path=root/name
        if sha in archives:path=Path(archives[sha])
        elif name in aliases:
            if type(aliases[name]) is not str or not Path(aliases[name]).is_absolute():
                raise ValueError('implementation alias requires an explicit absolute archive path')
            path=Path(aliases[name])
        _bound_file(path,sha,bound)
    return bound


def _preflight(document):
    if type(document) is not dict:raise ValueError('RF goal worker journal requires a JSON object')
    resumed=type(document.get('schema_version')) is int and document['schema_version']==2
    required=_REQUIRED+('resume_origin',) if resumed else _REQUIRED
    keys(document,required+('observed_cost','observed_bindings','stop_reason','observation_schema_version','observed_c_calls'),required,'RF goal worker journal')
    observation_version=document.get('observation_schema_version',1)
    if type(observation_version) is not int or observation_version not in (1,2):
        raise ValueError('RF observation schema must be original version 1 or linear-solve-aware version 2')
    if observation_version==2:
        from .curved_rf_goal_efficiency_observation import C_CALLS
        _same_saved(document.get('observed_c_calls'),C_CALLS,'RF original C-call observation scope')
    elif 'observed_c_calls' in document:raise ValueError('original observation version 1 cannot claim C-call coverage')
    try:_canonical(document)
    except (TypeError,ValueError,RecursionError,OverflowError) as error:
        raise ValueError('RF journal must contain finite JSON values') from error
    from .curved_rf_goal_efficiency_resume import RESUME_SCOPE,_origin_metadata
    if (type(document['schema_version']) is not int or document['schema_version'] not in (1,2) or
            document['document_type']!='curved_rf_goal_efficiency_worker_checkpoint' or document['physical_error_bound'] is not None or
            document['scope']!=(RESUME_SCOPE if resumed else _SCOPE)):raise ValueError('RF replay requires the complete original worker journal schema and scope')
    request=request_for_curved_rf_goal_efficiency_execution(document['execution'])
    _same_saved(document['request'],request,'saved RF original request')
    names=('events','level_runs','native_sources','event_records','observations')
    if any(type(document[k]) is not list for k in names):raise ValueError('RF journal requires every original event list')
    n=len(document['events']);limit=document['development_event_limit']
    if limit is not None:integer(limit,'development_event_limit')
    if resumed:_origin_metadata(document['resume_origin'],n)
    total_limit=None if limit is None else limit+(document['resume_origin']['event_count'] if resumed else 0)
    if not 1<=n<=request['max_levels'] or any(len(document[k])!=n for k in names) or (total_limit is not None and n>total_limit):
        raise ValueError('RF journal omitted events or exceeds the original event/development budget')
    for key in ('native_solves_attempted','native_solves_completed'):
        if type(document[key]) is not int or document[key]!=n:raise ValueError('completed RF prefix must retain every attempted/completed solve')
    if any(type(p) is not str for p in document['level_runs']) or len(set(document['level_runs']))!=n:
        raise ValueError('RF journal requires distinct native directory strings')
    uniform=document['execution']['method']=='uniform';public=document['public_checkpoint']
    if uniform:
        if public is not None or document['native_status']!='UNIFORM_CONTROL':raise ValueError('uniform control cannot supply a public RF checkpoint')
    elif (type(public) is not dict or type(public.get('level_runs')) is not list or
            not 1<=len(public['level_runs'])<=n or public['level_runs']!=document['level_runs'][:len(public['level_runs'])]):
        raise ValueError('public RF checkpoint must contain the entire original native prefix')
    bound={}
    for i,(run,event,record,observation) in enumerate(zip(document['level_runs'],document['events'],document['event_records'],document['observations'])):
        if type(run) is not str or not Path(run).is_absolute() or Path(run).name!=f'event-{i+1:03d}':
            raise ValueError('RF native runs must retain their absolute event paths and indices')
        for row in (event,record,observation):
            if type(row) is not dict or type(row.get('index')) is not int or row['index']!=i:
                raise ValueError('RF original event, record and observation indices differ')
        fields=('index','origin','run','domain','moments','fixed_moments_passed','ritz_passed','all_frequencies_hz','all_quantities','initial_independent_identity','samples','observed_prefix_cost')
        keys(record,fields,fields,'RF original event record')
        fields=('index','source_domain_identity_status','reference_orders','parent_change')
        keys(observation,fields,fields,'RF original observation')
        if record.get('run')!=run:raise ValueError('RF event record changed its original run')
        samples=record.get('samples')
        if (type(samples) is not list or len(samples)!=2 or any(type(s) is not dict or type(s.get('order')) is not int for s in samples) or
                [s['order'] for s in samples]!=[16,24]):
            raise ValueError('RF event requires both complete saved Gauss grids')
        for sample in samples:
            fields=('order','sample_path','sample_sha256','volume_sample_count','axis_sample_count','native_mode_count','reference_path','reference_sha256')
            keys(sample,fields,fields,'RF original sample record')
            expected=str(Path(run).parent/f'samples-event-{i+1:03d}-gauss-{sample["order"]}.npz')
            if sample.get('sample_path')!=expected:raise ValueError('RF sample does not belong to its original event directory')
            _bound_file(expected,sample['sample_sha256'],bound)
        actual=_native_files(Path(run))
        _same_saved(document['native_sources'][i],actual,'RF original native bytes')
        for name,sha in actual.items():_bound_file(Path(run)/name,sha,bound)
    _same_saved(document['events'][0].get('current_mode_ids'),request['initial_ids'],'RF initial declared IDs')
    metadata_assessment=assess_rf_goal_history(document['events'],document['observations'])
    _same_saved(document['assessment'],metadata_assessment,'RF saved scalar/ancestry assessment')
    if ('observed_cost' in document)!=('observed_bindings' in document):
        raise ValueError('completed RF cost and observed bindings must both be retained')
    if 'observed_bindings' in document:
        expected=[dict(module=m.__name__,attribute=a,phase=p) for m,a,p in observation_bindings()]
        _same_saved(document['observed_bindings'],expected,'RF original observation boundaries')
    if 'observed_cost' in document and document['status']=='PAUSED' and (total_limit is None or n!=min(total_limit,request['max_levels'])):
        raise ValueError('completed PAUSED worker must retain its actual development event limit')
    return request,bound


def replay_curved_rf_goal_efficiency(document, *, bindings=None, implementation_aliases=None, implementation_archives=None):
    """Recompute all native events, original mode fields and nine scalar gates.

    Exact original implementation bytes may be provided at explicit archive
    paths. They establish provenance, never executable state. Cost authenticity
    needs the caller's original journal SHA; this API checks its arithmetic.
    """
    document=deepcopy(document);implementation=_implementation_hashes()
    request,bound=_preflight(document)
    cost_document=document
    if document['schema_version']==2:
        from .curved_rf_goal_efficiency_resume import verify_resume_origin
        bound.update(verify_resume_origin(document,bindings=bindings,implementation_archives=implementation_archives))
        cost_document=dict(document,event_records=document['event_records'][document['resume_origin']['event_count']:])
    cost_status=_verify_costs(cost_document)
    bound.update(_implementation_sources(document['implementation_sha256'],implementation_aliases,implementation_archives))
    reference=load_curved_rf_goal_efficiency_reference(document['execution']['case_id'],bindings=bindings)
    _same_saved(document['reference_bound_inputs'],reference['bound_inputs'],'RF original independent reference bindings')
    bound.update(reference['bound_inputs']);case=Case.from_dict(request['case']);uniform=document['execution']['method']=='uniform'
    recorder=PhaseRecorder();events=[];observations=[];records=[];samples=[];runs=[];initial_identity=False;status='PAUSED'
    public=None;public_count=0 if uniform else len(document['public_checkpoint']['level_runs'])
    cache=None if uniform else native._VerifiedRFPrefix()
    if uniform:_,plan=curved.next_plan(case,request,[],None)
    else:public,plan=native.assemble(request,[],_cache=cache)
    current=None
    for i,run in enumerate(document['level_runs']):
        if status!='PAUSED':raise ValueError('RF journal contains an event after a terminal benchmark decision')
        continuation=not uniform and i>=public_count
        if not uniform and not continuation:
            public,following=native.assemble(request,document['level_runs'][:i+1],_cache=cache)
            event=deepcopy(public['levels'][-1]);current=cache.solution[-1]
            if i+1==public_count:_same_saved(document['public_checkpoint'],public,'complete original public RF checkpoint')
        else:
            if continuation and public['status']!='TARGETS_MET':
                raise ValueError('benchmark continuation requires a frozen successful public checkpoint')
            if i:
                next_case,source,_=_uniform_plan(case,request,current);plan=curved.Plan(next_case,source,None)
            event,current=_uniform_event(request,Path(run),events,runs,origin='uniform_control' if uniform else 'benchmark_confirmation')
            if current.case!=plan.case or mesh_digest(current.source_mesh_data)!=mesh_digest(plan.source_mesh):
                raise ValueError('uniform RF Case/source does not follow the prescribed actual parent')
        _same_saved(document['events'][i],event,'reconstructed complete RF event')
        domain=verify_efficiency_saved_domain(request,run);moments=mapped_moments(current.space)
        same_moments=not records or all(abs(v/records[0]['moments'][k]-1)<2e-12 for k,v in enumerate(moments))
        parent=event['parent_event_index']
        ritz=parent is None or bool(np.all(current.frequencies_hz<=np.asarray(records[parent]['all_frequencies_hz'])*(1+1e-10)))
        all_quantities=parse_json((Path(run)/'results.json').read_text())['modes']
        events.append(event);runs.append(run)
        observation,sample_rows,identity,initial_identity=_sample_event(request,reference,current,event,Path(run).parent,
            [] if parent is None else samples[parent],None if parent is None else events[parent],initial_identity,recorder,
            verify_samples=document['event_records'][i]['samples'])
        if not same_moments or not ritz:observation['source_domain_identity_status']='UNVERIFIED'
        _same_saved(document['observations'][i],observation,'RF full-field independent/parent metrics')
        observations.append(observation);samples.append(sample_rows)
        record=dict(index=i,origin='uniform_control' if uniform else 'benchmark_confirmation' if continuation else 'public_native',
                    run=run,domain=domain,moments=list(moments),fixed_moments_passed=same_moments,ritz_passed=ritz,
                    all_frequencies_hz=current.frequencies_hz.tolist(),all_quantities=all_quantities,
                    initial_independent_identity=identity if i==0 else None,samples=sample_rows,
                    observed_prefix_cost=deepcopy(document['event_records'][i]['observed_prefix_cost']))
        _same_saved(document['event_records'][i],record,'complete RF native event record');records.append(record)
        assessment=assess_rf_goal_history(events,observations)
        status=_stop_status(event,assessment,initial_identity=initial_identity,same_moments=same_moments,ritz=ritz,
                            native_status=None if uniform else public['status'],completed_events=i+1,max_events=request['max_levels'])
    _same_saved(document['assessment'],assessment,'RF original full-history acceptance')
    _same_saved(document['native_status'],'UNIFORM_CONTROL' if uniform else public['status'],'RF native status')
    if 'stop_reason' in document:
        if status!='PAUSED' or (not uniform and public['status']!='TARGETS_MET'):
            raise ValueError('RF uniform budget stop is not reachable from the original final prefix')
        try:_uniform_plan(case,request,current)
        except ValueError as error:
            if not any(word in str(error) for word in ('max_triangles','minimum_corner_angle_deg','TRACKING_BUDGET')):raise
            _same_saved(document['stop_reason'],str(error),'RF original uniform budget reason')
            status='TRACKING_BUDGET' if 'TRACKING_BUDGET' in str(error) else 'REFINEMENT_LIMIT'
        else:raise ValueError('RF journal claims a uniform budget stop that does not occur')
    _same_saved(document['status'],status,'RF benchmark stop')
    _verify_fixed_request(document['execution'],request);verify_reference_bytes(reference)
    for path,sha in bound.items():_bound_file(path,sha,{})
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during RF journal reconstruction')
    return dict(status='FULL_NATIVE_FIELDS_AND_DECISIONS_REPLAYED',document=document,
                bound_inputs=bound,cost_verification_status=cost_status,new_eigensolves=0,
                replay_observed_cost=recorder.finish(),physical_error_bound=None,
                scope='every declared source/native/sample byte, complete native events and all independent full-grid fields/metrics reconstructed; original elapsed costs retained, not remeasured; process/failure bundle and resume acceptance remain separate')


def read_curved_rf_goal_efficiency(path, *, expected_sha256, bindings=None, implementation_aliases=None, implementation_archives=None):
    """Bind the original raw journal bytes, including duplicate-key rejection."""
    bound={};path=_bound_file(path,expected_sha256,bound)
    document=parse_json(path.read_text(encoding='utf-8'));_bound_file(path,expected_sha256,{})
    result=replay_curved_rf_goal_efficiency(document,bindings=bindings,implementation_aliases=implementation_aliases,
                                          implementation_archives=implementation_archives)
    _bound_file(path,expected_sha256,{})
    result['bound_inputs'].update(bound)
    return result
