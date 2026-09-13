# SPDX-License-Identifier: Apache-2.0
"""Source-bound magnetic multipole reports with original FEM and Fourier replay."""
import hashlib,json,os,stat,tempfile
from pathlib import Path
from .config import keys,integer
from .project import parse_json
from .coaxial_saved import _json
from .planar_magnetostatic_saved import _snapshot,read_planar_magnetostatic_run
from .planar_bh_saved import read_planar_bh_run
from .planar_recoil_saved import read_planar_recoil_run
from .planar_magnetic_multipoles import PlanarMagneticMultipoleFrame
from .planar_magnetic_multipole_extraction import extract_planar_magnetic_multipoles


def multipole_request(data):
    names=['format','schema_version','frame','maximum_order','angular_samples'];keys(data,names,names,'planar magnetic multipole request')
    if data['format']!='superfish_ng_planar_magnetic_multipole_request' or type(data['schema_version']) is not int or data['schema_version']!=1:
        raise ValueError('unsupported planar magnetic multipole request format/version')
    frame=PlanarMagneticMultipoleFrame.from_dict(data['frame']);order=data['maximum_order'];count=data['angular_samples'];integer(order,'maximum_order');integer(count,'angular_samples')
    if not 1<=order<=32 or not 4*order<=count<=8192:raise ValueError('multipole request requires order 1..32 and 4*order<=angular_samples<=8192')
    return dict(format=data['format'],schema_version=1,frame=frame.to_dict(),maximum_order=order,angular_samples=count)


def _canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def _report_bytes(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('multipole report must be a regular file, not a symbolic link')
    descriptor=os.open(path,os.O_RDONLY|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(descriptor,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('multipole report must be a regular file')
        return stream.read()


def _outside(run,path):
    if path.resolve().is_relative_to(run.resolve()):raise ValueError('multipole report must be outside the source native directory')


def _compute(run,request):
    raw=_snapshot(run);manifest=parse_json(raw['manifest.json'].decode('utf-8'))
    readers={'superfish_ng_planar_magnetostatic_manifest':read_planar_magnetostatic_run,'superfish_ng_planar_bh_manifest':read_planar_bh_run,'superfish_ng_planar_recoil_manifest':read_planar_recoil_run}
    if not isinstance(manifest,dict) or type(manifest.get('format')) is not str or manifest['format'] not in readers:raise ValueError('multipole source requires a successful planar linear, B-H or recoil native manifest')
    source_format=manifest['format'];solution=readers[source_format](run)
    extraction=extract_planar_magnetic_multipoles(solution,PlanarMagneticMultipoleFrame.from_dict(request['frame']),request['maximum_order'],request['angular_samples'])
    result=dict(format='superfish_ng_planar_magnetic_multipole_report',schema_version=1,request=request,
        source_native_sha256={name:hashlib.sha256(value).hexdigest() for name,value in sorted(raw.items())},extraction=extraction,
        interpretation='Source-bound linear planar FEM spatial harmonics; replay requires the explicitly supplied unchanged five-file source native. Full FEM and Fourier replay is not a continuum error bound; no implicit material extension, force, torque or longitudinal integral.')
    if source_format!='superfish_ng_planar_magnetostatic_manifest':
        result.update(schema_version=2,source_native_manifest_format=source_format,source_physics=solution.case.to_dict()['physics'],interpretation='Source-bound planar B-H/recoil FEM harmonics in a verified declared homogeneous linear isotropic nonremanent source-free disk; explicit unchanged five-file native and original FEM/Fourier replay required; no continuum bound, GUI, force, torque or longitudinal integral.')
    if _snapshot(run)!=raw:raise ValueError('multipole source native changed during extraction')
    return result,raw


def export_planar_magnetic_multipoles(run,out,request):
    run,out=Path(run),Path(out);_outside(run,out);validated=multipole_request(request);result,raw=_compute(run,validated)
    if multipole_request(request)!=validated:raise ValueError('multipole request changed during extraction')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.planar-multipole-report-',dir=out.parent) as temporary:
        staged=Path(temporary)/'report.json';_json(staged,result)
        if _snapshot(run)!=raw:raise ValueError('multipole source native changed during report publication')
        os.link(staged,out)
    return result


def replay_planar_magnetic_multipoles(run,report):
    run,report=Path(run),Path(report);_outside(run,report);raw_report=_report_bytes(report);stored=parse_json(raw_report.decode('utf-8'))
    names=['format','schema_version','request','source_native_sha256','extraction','interpretation']
    if isinstance(stored,dict) and type(stored.get('schema_version')) is int and stored['schema_version']==2:names+=['source_native_manifest_format','source_physics']
    keys(stored,names,names,'planar magnetic multipole report')
    if stored['format']!='superfish_ng_planar_magnetic_multipole_report' or type(stored['schema_version']) is not int or stored['schema_version'] not in (1,2):
        raise ValueError('unsupported planar magnetic multipole report format/version')
    request=multipole_request(stored['request']);raw=_snapshot(run)
    if stored['source_native_sha256']!={name:hashlib.sha256(value).hexdigest() for name,value in sorted(raw.items())}:
        raise ValueError('multipole report source native hashes disagree')
    expected,verified_raw=_compute(run,request)
    if verified_raw!=raw or _snapshot(run)!=raw:raise ValueError('multipole source native changed during replay')
    if _canonical(stored)!=_canonical(expected):raise ValueError('saved multipole report coefficients, original fields, disk, diagnostics or conventions disagree with FEM/Fourier replay')
    if _report_bytes(report)!=raw_report:raise ValueError('multipole report changed during replay')
    return expected
