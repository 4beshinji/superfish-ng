# SPDX-License-Identifier: Apache-2.0
"""Public inventory for dedicated Hphi inputs and versioned planar mappings.

This is descriptive metadata. Case parsers and numerical validators remain the
authority for accepting any input; adding an entry never enables a solver.
"""


def hphi_capabilities():
    families = []
    for name, geometry, axes, command in (
        ('coaxial', 'closed coaxial cylinder', [False], 'coaxial'),
        ('hphi_mesh', 'explicit straight meridional triangles with PEC holes', [False], 'hphi-mesh'),
        ('axis_hphi', 'explicit straight meridional triangles with one vacuum axis interval and PEC holes', [True], 'axis-hphi'),
        ('curved_hphi', 'explicit quadratic polynomial triangles with PEC holes; all vertices and edge midpoints supplied', [False, True], 'curved-hphi'),
    ):
        families.append(dict(case_format=f'superfish_ng_{name}_case', case_schema_versions=[1],
            native_manifest_format=f'superfish_ng_{name}_manifest', native_schema_versions=[1],
            result_format=f'superfish_ng_{name}_result', result_schema_versions=[1],
            geometry=geometry, axis_connected=axes, element_orders=[1, 2],
            commands=[f'solve-{command}', f'replay-{command}', f'probe-{command}'],
            same_domain_comparison=name!='curved_hphi',
            cylinder_dimension_sweeps=name=='coaxial'))
    return dict(case_families=families, physics='rf_eigenmode', coordinates='axisymmetric r,z',
        azimuthal_index=0, field_family='Hphi', material='vacuum', boundary='closed PEC',
        formulations=dict(
            positive_radius=dict(scalar='q = r*Hphi', coefficient_unit='A', excluded_static_modes=1,
                static_field='constant q; Hphi proportional to 1/r', axis_acceleration=False),
            axis_connected=dict(scalar='u = Hphi/r', coefficient_unit='A/m^2', excluded_static_modes=0,
                axis_condition='retain all regular finite-u axis degrees of freedom', axis_acceleration='explicit vacuum-axis path only')),
        spectrum='lowest positive FEM frequencies; mode index is frequency rank, not a tracked identity',
        volume_measure='2*pi*r dr dz; full 3D vacuum excluding PEC holes', energy_unit='J', wall_loss_unit='W',
        phasor='peak exp(+i omega t); Hphi real, Er/Ez quadrature; field = real + i*quadrature',
        field_units=dict(E='V/m', H='A/m', B='T'), magnetic_flux_density='B = mu0 H',
        acceleration=dict(path='axis', required_parameters=['z_start_m','z_end_m','beta','phase_origin_m'],
            absent_path='Vacc, Eacc and both R/Q definitions are null/N/A',
            rq_definitions=dict(accelerator='abs(Vacc)^2/(omega*U)', circuit='abs(Vacc)^2/(2*omega*U)')),
        project=dict(format='superfish_ng_hphi_project', version=1, display_length_units=['m','mm'],
            stored_coordinates='SI metres', job_kind='hphi_solve', gui='/hphi.html',
            operations=['execute-hphi-project','plot-hphi','probe-hphi-csv'],
            manager_operations=['start_hphi','import_hphi_result','cancel','status','list'],
            plot='signed original-cell fields; curved boundaries retained; no surface-peak accuracy claim'),
        study=dict(format='superfish_ng_hphi_study', version=1, kind='sweep',
            common_parameters=['uniform_scale','/case/rf/stored_energy_j','/case/rf/conductivity_s_per_m'],
            coaxial_only_parameters=['/case/geometry/inner_radius_m','/case/geometry/outer_radius_m','/case/geometry/length_m'],
            commands=['execute-hphi-study','replay-hphi-study'], mode_tracking='not_performed'),
        comparison=dict(case_formats=[f['case_format'] for f in families if f['same_domain_comparison']],
            geometry='exactly the same straight meridional vacuum; explicit original and comparison meshes',
            field_inner_products='separate original E and H with full 3D volume measure',
            scalar_projection='mass L2 projection; projected coefficients are not eigenmodes',
            spectral_resolution='finite comparison-space diagnostic; no continuum error bound or guaranteed rank',
            convergence=dict(format='superfish_ng_hphi_convergence', version=1,
                commands=['execute-hphi-convergence','replay-hphi-convergence'],
                scope='three or more explicit levels; separate f/E/H/RF and wall-segment differences; ambiguous modes remain UNVERIFIED'),
            tracking=dict(format='superfish_ng_hphi_tracking_request', version=1, mapping='same_vacuum',
                commands=['execute-hphi-tracking','replay-hphi-tracking'],
                scope='guarded finite positive bands; E/H subspace correspondence; degenerate groups retain ID sets'),
            history=dict(format='superfish_ng_hphi_tracking_history_request', version=1,
                commands=['execute-hphi-history','extend-hphi-history','replay-hphi-history'],
                scope='fully replayed owned native chain; exact band and identity continuity; unresolved final step stops extension')),
        limits=['No materials, open ports, azimuthal m>0 or general 3D fields',
            'Curved geometry is quadratic polynomial, not an exact conic or an automatic curved mesh generator',
            'Curved field comparison, convergence diagnostics, projection, spectral comparison and tracking are unsupported',
            'No general shape-deformation identity, continuous-spectrum error bound or surface-peak accuracy guarantee'])


def planar_tracking_mappings():
    return [dict(version=version, name=name, scope=scope) for version, name, scope in (
        (1, 'normalized_rectangle', 'rectangular cases on a normalized rectangle'),
        (2, 'polygon_uniform_scale', 'declared uniform scale and nested original/refined polygon meshes'),
        (3, 'polygon_similarity', 'declared proper similarity and nested polygon meshes'),
        (4, 'polygon_same_domain', 'independent meshes of exactly the same polygon'),
        (5, 'polygon_similarity_remesh', 'proper similarity with exactly matching transformed boundary subdivision; independent interior'),
        (6, 'polygon_affine_remesh', 'invertible affine map with exactly matching transformed boundary subdivision; independent interior'),
        (7, 'polygon_exact_affine_remesh', 'rationally evaluated invertible affine map; independent boundary and interior subdivisions'),
    )]
