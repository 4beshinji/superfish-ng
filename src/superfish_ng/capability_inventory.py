# SPDX-License-Identifier: Apache-2.0
"""Public inventory for dedicated RF/static inputs and planar mappings.

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


def material_hphi_capabilities():
    return dict(case_format='superfish_ng_material_hphi_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_material_hphi_manifest',native_schema_versions=[1],
        result_format='superfish_ng_material_hphi_result',result_schema_versions=[1],
        partition_format='superfish_ng_rf_material_partition',partition_schema_versions=[1],
        commands=['solve-material-hphi','replay-material-hphi','probe-material-hphi'],
        physics='rf_eigenmode',coordinates='axisymmetric r,z',azimuthal_index=0,field_family='Hphi',boundary='closed PEC',
        geometry='explicit straight material-conforming meridional triangles, optional axis and PEC holes',
        element_orders=[1,2],axis_connected=[False,True],
        material='positive real isotropic linear nondispersive lossless epsilon_r/mu_r, constant in each explicitly assigned cell',
        formulations=dict(positive_radius='q=r*Hphi, A; remove one constant static mode',
            axis_connected='u=Hphi/r, A/m^2; retain every regular axis DOF, remove no mode'),
        phasor='peak exp(+i omega t); Hphi real, Er/Ez quadrature; field=real+i*quadrature',
        fields='E uses epsilon_r(original cell); B=mu0*mu_r(original cell)*H',
        probes='18 SI E/H/B components, original cell, region/material IDs and coefficients; lowest original cell at interfaces, no averaging',
        volume_measure='2*pi*r dr dz; full 3D',energy_unit='J',wall_loss_unit='W',
        energy='integral (epsilon0*epsilon_r*|E|^2+mu0*mu_r*|H|^2)/4 dV; electric and magnetic by region',
        wall_model='nonmagnetic metal; Rs=sqrt(pi*f*mu0/sigma), independent of adjacent material mu_r; no volume loss',
        acceleration='explicit axis interval with epsilon_r=mu_r=1 on every overlapping axis segment; absent path gives null/N/A',
        rq_definitions=dict(accelerator='abs(Vacc)^2/(omega*U)',circuit='abs(Vacc)^2/(2*omega*U)'),
        project=dict(format='superfish_ng_hphi_project',version=1,command='execute-hphi-project',job_kind='hphi_solve'),
        gui='/hphi.html',study=dict(format='superfish_ng_hphi_study',version=1,kind='sweep',
            parameters=['uniform_scale','/case/rf/stored_energy_j','/case/rf/conductivity_s_per_m'],
            commands=['execute-hphi-study','replay-hphi-study'],mode_tracking='not_performed'),tracking=False,
        display=dict(commands=['plot-hphi','probe-hphi-csv'],
            policy='original material E/H/B; CSV includes one-sided cell and region/material IDs with epsilon_r/mu_r'),
        limits=['No curved cells, complex/dispersive/anisotropic/nonlinear materials or volume conductivity',
            'No material coefficient sweeps, field comparison, convergence diagnostics or tracking',
            'No open ports, azimuthal m>0 or static-field solver',
            'No continuum error bound or surface-peak accuracy guarantee; mode rank is not identity'])


def electrostatic_capabilities():
    return dict(case_format='superfish_ng_axisymmetric_electrostatic_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_axisymmetric_electrostatic_manifest',native_schema_versions=[1],
        result_format='superfish_ng_axisymmetric_electrostatic_result',result_schema_versions=[1],
        partition_format='superfish_ng_axisymmetric_dielectric_partition',partition_schema_versions=[1],
        commands=['solve-electrostatic','replay-electrostatic','probe-electrostatic'],physics='linear_electrostatic',
        coordinates='axisymmetric r,z',geometry='explicit straight dielectric-conforming meridional triangles, optional axis and holes',
        element_orders=[1,2],axis_connected=[False,True],material='positive real isotropic linear epsilon_r, explicit in every cell',
        volume_charge='signed rho [C/m^3], explicit in every region',
        boundaries=['electrode_potential [V]','outward_displacement [C/m^2]','axis_symmetry'],
        boundary_policy='every edge explicit, at least one electrode; connected conductor edges share one electrode id',
        potential='Phi [V], coefficients relative to first fixed electrode; retain all axis DOFs',
        fields='static real E=-grad(Phi) [V/m], D=epsilon0*epsilon_r(original cell)*E [C/m^2]',
        probes='original Phi/Er/Ez/Dr/Dz, cell/region/material IDs and epsilon_r; lowest cell at interfaces, no averaging',
        volume_measure='2*pi*r dr dz; full 3D',energy='integral epsilon*|E|^2/2 dV [J]',charge_unit='C',
        electrode_charge='separate discrete reaction and minus original outward D flux into electrode',
        capacitance='F, only two unequal fixed electrodes with rho=0 and other non-axis Dn=0; reaction, energy and original-field definitions separate',
        project=False,gui=False,study=False,
        limits=['No planar/curved geometry, nonlinear/anisotropic/complex permittivity or RF phasors',
            'No pure Neumann/gauge, floating electrodes, multi-terminal capacitance matrix or exact open boundary',
            'Discrete residual and reaction conservation do not bound original field or surface-flux error'])


def planar_electrostatic_capabilities():
    return dict(case_format='superfish_ng_planar_electrostatic_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_planar_electrostatic_manifest',native_schema_versions=[1],
        result_format='superfish_ng_planar_electrostatic_result',result_schema_versions=[1],
        partition_format='superfish_ng_planar_dielectric_partition',partition_schema_versions=[1],
        commands=['solve-planar-electrostatic','replay-planar-electrostatic','probe-planar-electrostatic'],physics='linear_electrostatic',
        coordinates='Cartesian x,y',geometry='explicit straight dielectric-conforming triangles in a simple polygon',
        element_orders=[1,2],material='positive real isotropic linear epsilon_r, explicit in every cell',
        volume_charge='signed rho [C/m^3], explicit in every region',
        boundaries=['electrode_potential [V]','outward_displacement [C/m^2]'],
        boundary_policy='every edge explicit, at least one electrode; connected conductor edges share one electrode id',
        potential='Phi [V], coefficients relative to first fixed electrode; no implicit ground, axis or thickness',
        fields='static real E=-grad(Phi) [V/m], D=epsilon0*epsilon_r(original cell)*E [C/m^2]',
        probes='original Phi/Ex/Ey/Dx/Dy, cell/region/material IDs and epsilon_r; lowest cell at interfaces, no averaging',
        volume_measure='dx dy per metre of uniform extrusion',energy='integral epsilon*|E|^2/2 dxdy [J/m]',charge_unit='C/m',
        electrode_charge='separate discrete reaction and minus original outward D flux into electrode',
        capacitance='F/m, only two unequal fixed electrodes with rho=0 and other Dn=0; reaction, energy and original-field definitions separate',
        project=False,gui=False,study=False,
        limits=['No axisymmetric/curved geometry or holes, nonlinear/anisotropic/complex permittivity or RF phasors',
            'No pure Neumann/gauge, floating electrodes, multi-terminal capacitance matrix or exact open boundary',
            'Discrete residual and reaction conservation do not bound original field or surface-flux error'])


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


def planar_magnetostatic_capabilities():
    return dict(case_format='superfish_ng_planar_magnetostatic_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_planar_magnetostatic_manifest',native_schema_versions=[1],
        result_format='superfish_ng_planar_magnetostatic_result',result_schema_versions=[1],
        partition_format='superfish_ng_planar_magnetic_partition',partition_schema_versions=[1],
        commands=['solve-planar-magnetostatic','replay-planar-magnetostatic','probe-planar-magnetostatic'],physics='linear_magnetostatic',
        coordinates='Cartesian x,y',geometry='explicit straight material-conforming triangles in a simple polygon',
        element_orders=[1,2],material='positive real isotropic linear mu_r, explicit in every cell; reluctivity=(1/mu0)/mu_r [m/H]',
        volume_current='signed Jz [A/m^2], explicit in every region',
        boundaries=['fixed_az [Wb/m]','tangential_h [A/m]'],
        boundary_policy='every edge explicit; at least one fixed-Az boundary; connected fixed edges share one boundary id; counterclockwise tangent',
        potential='Az [Wb/m], coefficients relative to first fixed boundary; no implicit ground, axis or thickness',
        fields='static real B=(dAz/dy,-dAz/dx) [T], H=reluctivity(original cell)*B [A/m]',
        probes='original Az/Bx/By/Hx/Hy, cell/region/material IDs and mu_r; lowest cell at interfaces, no averaging',
        volume_measure='dx dy per metre of uniform extrusion',energy='integral |B|^2/(2*mu0*mu_r) dxdy [J/m]',current_unit='A',
        fixed_boundary_reaction='separate discrete reaction and minus original counterclockwise H line integral [A]',
        normal_flux='original B dot outward normal integrated along boundary [Wb/m]; normal to right of tangent',
        project=False,gui=False,study=False,
        limits=['No axisymmetric/curved geometry or holes, nonlinear/anisotropic/complex permeability, remanence or RF phasors',
            'No pure Neumann/gauge, winding inductance or exact open boundary',
            'Discrete residual and reaction conservation do not bound original field or circulation error'])


def axis_magnetostatic_capabilities():
    return dict(case_format='superfish_ng_axis_magnetostatic_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_axis_magnetostatic_manifest',native_schema_versions=[1],
        result_format='superfish_ng_axis_magnetostatic_result',result_schema_versions=[1],
        partition_format='superfish_ng_axis_magnetic_partition',partition_schema_versions=[1],
        commands=['solve-axis-magnetostatic','replay-axis-magnetostatic','probe-axis-magnetostatic'],physics='linear_magnetostatic',
        coordinates='axisymmetric r,z',geometry='explicit straight axis-connected triangles, optional holes',
        element_orders=[1,2],material='positive real isotropic linear mu_r, explicit in every cell',
        volume_current='signed Jphi [A/m^2], explicit in every region; cross-section integral Jphi dr dz [A]',
        boundaries=['fixed_aphi_over_r [T]','tangential_h [A/m]','axis_regularity'],
        boundary_policy='every edge explicit; axis regularity only at r=0; domain-left tangent in r,z; all non-axis Ht is allowed',
        potential='a=Aphi/r [T], Aphi=r*a [Wb/m]; all axis a DOFs retained; constant a is uniform Bz, not gauge',
        fields='Br=-r*d_z(a) [T], Bz=2*a+r*d_r(a) [T], H=reluctivity(original cell)*B [A/m]',
        probes='original a/Aphi/Br/Bz/Hr/Hz, cell/region/material IDs and mu_r; lowest cell at interfaces, no averaging',
        volume_measure='2*pi*r dr dz; full 3D',energy='integral |B|^2/(2*mu0*mu_r) dV [J]',current_unit='A',
        fixed_boundary_reaction='separate discrete reaction and +2*pi*integral r^2*Ht ds [A m^2]; conjugate to a, not Ampere current',
        normal_flux='2*pi*integral r*original B dot outward normal ds [Wb]',
        project=False,gui=False,study=False,
        limits=['No off-axis gauge or curved geometry, nonlinear/anisotropic/complex permeability, remanence or RF phasors',
            'No winding inductance or exact open boundary',
            'Discrete work identities do not bound original field, flux or circulation error'])


def off_axis_magnetostatic_capabilities():
    return dict(case_format='superfish_ng_off_axis_magnetostatic_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_off_axis_magnetostatic_manifest',native_schema_versions=[1],
        result_format='superfish_ng_off_axis_magnetostatic_result',result_schema_versions=[1],
        partition_format='superfish_ng_off_axis_magnetic_partition',partition_schema_versions=[1],
        commands=['solve-off-axis-magnetostatic','replay-off-axis-magnetostatic','probe-off-axis-magnetostatic'],physics='linear_magnetostatic',
        coordinates='axisymmetric r,z with strictly r>0',geometry='explicit straight material-conforming triangles, optionally with declared holes',
        element_orders=[1,2],material='positive real isotropic linear mu_r; reluctivity=(1/mu0)/mu_r [m/H]',
        volume_current='signed Jphi [A/m^2], explicit in every region',boundaries=['fixed_psi [Wb]','tangential_h [A/m]'],
        boundary_policy='every edge explicit; at least one fixed-psi boundary; connected fixed edges share one id; domain on left of tangent',
        potential='psi=r*Aphi [Wb], coefficients relative to first fixed-psi boundary; constant psi is zero B with curl-free Aphi=C/r',
        fields='Br=-d_z(psi)/r, Bz=d_r(psi)/r [T], H=reluctivity(original cell)*B [A/m]',
        probes='original psi/Aphi/Br/Bz/Hr/Hz, cell/region/material IDs and mu_r; lowest cell at interfaces, no averaging',
        volume_measure='2*pi*r drdz',energy='integral |B|^2/(2*mu0*mu_r) 2*pi*r drdz [J]',current_unit='A',
        fixed_boundary_reaction='separate discrete reaction and +2*pi integral original Ht ds [A]',
        normal_flux='original 2*pi*r B dot outward normal integrated along domain boundary [Wb]',
        project=False,gui=False,study=False,
        limits=['No axis-connected/curved geometry, nonlinear/anisotropic/complex permeability, remanence or RF phasors',
            'No pure Neumann, excluded-axis absolute linked flux, winding inductance or exact open boundary',
            'Discrete residual and reaction conservation do not bound original field or circulation error'])


def planar_recoil_capabilities():
    return dict(case_format='superfish_ng_planar_recoil_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_planar_recoil_manifest',native_schema_versions=[1],
        result_format='superfish_ng_planar_recoil_result',result_schema_versions=[1],
        partition_format='superfish_ng_planar_recoil_partition',partition_schema_versions=[1],
        commands=['solve-planar-recoil','replay-planar-recoil','probe-planar-recoil'],physics='linear_recoil_magnetostatic',
        coordinates='Cartesian x,y',geometry='explicit straight material-conforming triangles in a simple polygon',element_orders=[1,2],
        material='positive principal recoil mu_r, local remanent induction[T] and explicit region orientation[rad]; B=mu0*mu_rec*H+Brem',
        volume_current='signed free Jz [A/m^2], explicit in every region',boundaries=['fixed_az [Wb/m]','tangential_h [A/m]'],
        boundary_policy='every edge explicit; at least one fixed-Az boundary; connected fixed edges share one id; domain-left tangent',
        potential='Az[Wb/m] relative to first fixed-Az boundary with original reference retained',
        fields='B=(dAz/dy,-dAz/dx)[T], H=nu(original cell)*(B-Brem)[A/m]',
        probes='original Az/Bx/By/Hx/Hy, cell/region/material IDs, tensor and remanent B; exact binary64 cell ownership, no averaging',
        volume_measure='dx dy per metre of uniform extrusion',
        constitutive_potentials='B=0 and H=0 references explicitly named [J/m]; difference is .5 integral Brem.nu.Brem; no absolute magnet internal energy',
        current_unit='A',fixed_boundary_reaction='separate discrete reaction and minus original domain-left Ht integral [A]',
        normal_flux='original B dot outward normal integrated along boundary [Wb/m]',project=False,gui=False,study=False,
        limits=['No axisymmetric/curved geometry or holes, nonlinear/complex permeability, hysteresis or RF phasors',
            'No pure Neumann, irreversible demagnetization, winding inductance, force or exact open boundary',
            'Discrete residual and reaction conservation do not bound original field or circulation error'])


def axis_recoil_capabilities():
    return dict(case_format='superfish_ng_axis_recoil_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_axis_recoil_manifest',native_schema_versions=[1],
        result_format='superfish_ng_axis_recoil_result',result_schema_versions=[1],
        partition_format='superfish_ng_axis_recoil_partition',partition_schema_versions=[1],
        commands=['solve-axis-recoil','replay-axis-recoil','probe-axis-recoil'],physics='linear_recoil_magnetostatic',
        coordinates='axisymmetric r,z',geometry='explicit straight axis-connected material-conforming triangles, optional off-axis holes',element_orders=[1,2],
        material='positive principal recoil mu_r, local remanent B[T], meridional region orientation[rad]; B=mu0*mu_rec*H+Brem',
        axis_material='axis-touching region orientation=0 and radial remanence=0; no phi coupling, mu_phi=mu_rr, remanent B_phi=0',
        volume_current='signed free Jphi[A/m^2], explicit in every region; cross-section integral is current[A]',
        boundaries=['fixed_aphi_over_r [T]','tangential_h [A/m]','axis_regularity'],
        boundary_policy='every edge explicit; axis_regularity only at r=0; all external Ht supported without a gauge kernel',
        potential='a=Aphi/r[T], Aphi=r*a[Wb/m]; all axis a DOFs retained',
        fields='Br=-r*a_z, Bz=2a+r*a_r [T], H=nu(original cell)*(B-Brem)[A/m]; Aphi=Br=Hr=0 at axis',
        probes='original a/Aphi/Br/Bz/Hr/Hz with cell/region/material IDs, tensor/remanence and orientation; no averaging',
        volume_measure='2*pi*r dr dz, full 3D',constitutive_potentials='B=0 and H=0 references explicitly named [J]; no absolute magnet internal energy',
        fixed_boundary_reaction='positive 2*pi integral r^2 Ht ds [A m^2], conjugate to a[T]; original and discrete values separate',
        normal_flux='2*pi integral r*original B dot outward normal ds [Wb]',project=False,gui=False,study=False,
        limits=['No off-axis-only domain, curved geometry, arbitrary 3D tensor, nonlinear/complex permeability, hysteresis or RF phasors',
            'No irreversible demagnetization, winding inductance, force or exact open boundary',
            'Discrete residual and work identities do not bound original field or circulation error'])


def off_axis_recoil_capabilities():
    return dict(case_format='superfish_ng_off_axis_recoil_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_off_axis_recoil_manifest',native_schema_versions=[1],
        result_format='superfish_ng_off_axis_recoil_result',result_schema_versions=[1],
        partition_format='superfish_ng_off_axis_recoil_partition',partition_schema_versions=[1],
        commands=['solve-off-axis-recoil','replay-off-axis-recoil','probe-off-axis-recoil'],physics='linear_recoil_magnetostatic',
        coordinates='axisymmetric r,z, strictly r>0',geometry='explicit straight material-conforming triangles, optional holes; axis excluded',element_orders=[1,2],
        material='positive principal recoil mu_r, local remanent B[T] and meridional region orientation[rad]; B=mu0*mu_rec*H+Brem',
        azimuthal_model='no phi coupling, mu_phi=mu_rr and remanent B_phi=0',volume_current='signed free Jphi[A/m^2], explicit in every region',
        boundaries=['fixed_psi [Wb]','tangential_h [A/m]'],boundary_policy='every edge explicit; at least one fixed psi; connected fixed edges share one id',
        potential='psi=r*Aphi[Wb]; relative and absolute psi with reference retained; constant shift adds C/r to Aphi',
        fields='Br=-psi_z/r, Bz=psi_r/r[T], original H=nu*(B-Brem)[A/m]',
        probes='original psi/Aphi/Br/Bz/Hr/Hz with cell/region/material IDs, tensor/remanence and orientation; no averaging',
        volume_measure='2*pi*r dr dz, full 3D',constitutive_potentials='B=0 and H=0 references explicitly named [J]; no absolute magnet internal energy',
        fixed_boundary_reaction='+2*pi integral original Ht ds [A], distinct from the discrete reaction',
        normal_flux='2*pi integral r*original B dot outward normal ds [Wb]; excluded-axis absolute flux is not inferred',project=False,gui=False,study=False,
        limits=['No axis-connected/curved geometry, arbitrary 3D tensor, nonlinear/complex permeability, hysteresis or RF phasors',
            'No pure Neumann, irreversible demagnetization, winding inductance, force or exact open boundary',
            'Discrete residual and identities do not bound original field or circulation error'])


def planar_bh_capabilities():
    return dict(case_format='superfish_ng_planar_bh_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_planar_bh_manifest',native_schema_versions=[1],
        failure_manifest_format='superfish_ng_planar_bh_failure_manifest',failure_schema_versions=[1],
        result_format='superfish_ng_planar_bh_result',result_schema_versions=[1],
        failure_format='superfish_ng_magnetic_nonlinear_failure',
        partition_format='superfish_ng_planar_bh_partition',partition_schema_versions=[1],
        commands=['solve-planar-bh','replay-planar-bh','probe-planar-bh'],physics='nonlinear_isotropic_magnetostatic',
        coordinates='cartesian x,y',geometry='explicit straight simple polygon and material-conforming triangles',element_orders=[1],
        material='explicit monotone piecewise-linear H(B) in SI with provenance; isotropic, reversible, no extrapolation',
        volume_current='signed Jz[A/m^2], explicit in every region',boundaries=['fixed_az [Wb/m]','tangential_h [A/m]'],
        boundary_policy='every edge explicit; at least one fixed Az; first fixed value defines the retained reference',
        nonlinear_method='true material tangent, damped Newton with objective line search and separate residual convergence',
        failure='separate verified failure native retains Case, controls, complete history and last valid relative coefficients or null; replay reattempts the same FEM',
        cli_exit_codes=dict(success=0,nonlinear_failure=1,input_or_native_error=2),
        fields='Az[Wb/m], original B=curl(Az ez)[T], H=h(|B|)*B/|B|[A/m]',
        probes='original one-sided P1 fields with cell/region/material IDs, provenance, table interval and secant/differential reluctivity; no averaging',
        volume_measure='dx dy per metre of uniform extrusion',energy='U=integral h(b) db dA; Ustar=integral b(h) dh dA [J/m]; internal work=U+Ustar',
        fixed_boundary_reaction='minus original Ht line integral [A], distinct from discrete reaction',normal_flux='original B dot outward normal line integral [Wb/m]',
        native_replay='same nonlinear FEM with exact coefficient and deterministic iteration-history comparison',project=False,gui=False,study=False,
        limits=['No P2, axisymmetric/curved geometry, pure Neumann, anisotropic nonlinear material, hysteresis or remanence',
            'No RF phasors, winding inductance, force or exact open boundary',
            'Algebraic convergence and discrete identities do not bound original field or circulation error'])


def axis_bh_capabilities():
    return dict(case_format='superfish_ng_axis_bh_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_axis_bh_manifest',native_schema_versions=[1],
        failure_manifest_format='superfish_ng_axis_bh_failure_manifest',failure_manifest_schema_versions=[1],failure_schema_versions=[2],
        result_format='superfish_ng_axis_bh_result',result_schema_versions=[1],failure_format='superfish_ng_magnetic_nonlinear_failure',
        failure_coefficient_field='aphi_over_r_t',partition_format='superfish_ng_axis_bh_partition',partition_schema_versions=[1],
        commands=['solve-axis-bh','replay-axis-bh','probe-axis-bh'],physics='nonlinear_isotropic_magnetostatic',
        coordinates='axisymmetric r,z',geometry='explicit straight axis-connected triangles with optional holes',element_orders=[1],quadrature_order_range=[4,32],
        material='explicit monotone piecewise-linear H(B) in SI with provenance; isotropic H parallel to B, Bphi=Hphi=0, no extrapolation',
        volume_current='signed Jphi[A/m^2], explicit in every region',boundaries=['fixed_aphi_over_r [T]','tangential_h [A/m]','axis_regularity'],
        boundary_policy='every edge explicit; all axis DOFs retained; all non-axis Ht is allowed; constant a is not a gauge',
        nonlinear_method='true material tangent, damped Newton with objective line search and separate fixed-quadrature residual convergence',
        failure='separate version-2 report retains Case, controls, complete history, coefficient_field=aphi_over_r_t and last_valid_coefficients or null; replay reattempts the same FEM',
        cli_exit_codes=dict(success=0,nonlinear_failure=1,input_or_native_error=2),
        fields='a=Aphi/r[T], Aphi[Wb/m], Br=-r*a_z, Bz=2*a+r*a_r[T], original H=h(|B|)*B/|B|[A/m]',
        probes='original one-sided six fields with cell/region/material IDs, provenance, table interval and secant/differential reluctivity; no averaging',
        volume_measure='2*pi*r dr dz, full 3D',energy='U=integral h(b) db dV; Ustar=integral b(h) dh dV [J]; internal work=U+Ustar',
        fixed_boundary_reaction='+2*pi integral r^2 original Ht ds [A m^2], distinct from discrete reaction or current[A]',normal_flux='2*pi integral r original B dot outward normal ds [Wb]',
        native_replay='same nonlinear FEM with exact coefficient, deterministic iteration and q/q+4 diagnostic comparison',project=False,gui=False,study=False,
        limits=['No P2, off-axis/curved geometry, anisotropic nonlinear material, hysteresis or remanence',
            'No RF phasors, winding inductance, force or exact open boundary',
            'Algebraic convergence and discrete identities do not bound quadrature or original field/circulation error'])


def off_axis_bh_capabilities():
    return dict(case_format='superfish_ng_off_axis_bh_case',case_schema_versions=[1],
        native_manifest_format='superfish_ng_off_axis_bh_manifest',native_schema_versions=[1],
        failure_manifest_format='superfish_ng_off_axis_bh_failure_manifest',failure_manifest_schema_versions=[1],failure_schema_versions=[2],
        result_format='superfish_ng_off_axis_bh_result',result_schema_versions=[1],failure_format='superfish_ng_magnetic_nonlinear_failure',
        failure_coefficient_field='psi_relative_to_reference_wb',partition_format='superfish_ng_off_axis_bh_partition',partition_schema_versions=[1],
        commands=['solve-off-axis-bh','replay-off-axis-bh','probe-off-axis-bh'],physics='nonlinear_isotropic_magnetostatic',
        coordinates='axisymmetric r,z',geometry='explicit straight positive-radius triangles with optional holes',element_orders=[1],quadrature_order_range=[4,32],
        material='explicit monotone piecewise-linear H(B) in SI with provenance; isotropic H parallel to B, Bphi=Hphi=0, no extrapolation',
        volume_current='signed Jphi[A/m^2], explicit in every region',boundaries=['fixed_psi [Wb]','tangential_h [A/m]'],
        boundary_policy='every edge explicit; at least one fixed psi; pure Neumann gauge is unsupported; psi reference retained',
        nonlinear_method='true material tangent, damped Newton with objective line search and separate fixed-quadrature residual convergence',
        failure='separate version-2 report retains Case, controls, complete history, coefficient_field=psi_relative_to_reference_wb and last_valid_coefficients or null; replay reattempts the same FEM',
        cli_exit_codes=dict(success=0,nonlinear_failure=1,input_or_native_error=2),
        fields='psi[Wb], Aphi=psi/r[Wb/m], Br=-psi_z/r, Bz=psi_r/r[T], original H=h(|B|)*B/|B|[A/m]',
        probes='original one-sided six fields with cell/region/material IDs, provenance, table interval and secant/differential reluctivity; no averaging',
        volume_measure='2*pi*r dr dz, full 3D',energy='U=integral h(b) db dV; Ustar=integral b(h) dh dV [J]; internal work=U+Ustar',
        fixed_boundary_reaction='+2*pi integral original Ht ds [A], distinct from discrete reaction',normal_flux='2*pi integral r original B dot outward normal ds [Wb]',
        native_replay='same nonlinear FEM with exact coefficient, deterministic iteration and q/q+4 diagnostic comparison',project=False,gui=False,study=False,
        limits=['No P2, axis-connected/curved geometry, anisotropic nonlinear material, hysteresis or remanence',
            'No RF phasors, winding inductance, force or exact open boundary',
            'Algebraic convergence and discrete identities do not bound quadrature or original field/circulation error'])


def planar_magnetic_multipole_capabilities():
    return dict(request_format='superfish_ng_planar_magnetic_multipole_request',request_schema_versions=[1],
        report_format='superfish_ng_planar_magnetic_multipole_report',report_schema_versions=[1,2],
        source_native_manifest_format='superfish_ng_planar_magnetostatic_manifest',source_native_schema_versions=[1],
        source_native_manifest_formats=['superfish_ng_planar_magnetostatic_manifest','superfish_ng_planar_bh_manifest','superfish_ng_planar_recoil_manifest'],
        source_element_orders={'linear_magnetostatic':[1,2],'nonlinear_isotropic_magnetostatic':[1],'linear_recoil_magnetostatic':[1,2]},
        series_format='superfish_ng_planar_magnetic_multipole_series',series_schema_versions=[1],
        extraction_format='superfish_ng_planar_magnetic_multipole_extraction',extraction_schema_versions=[1,2],
        commands=['extract-planar-magnetic-multipoles','replay-planar-magnetic-multipoles'],element_orders=[1,2],
        coefficient_unit='T',convention='local By+iBx; normal+i*skew; n=1..32; explicit center[m], radius[m], counterclockwise rotation[rad]',
        aperture='whole closed disk strictly inside original domain; exact zero Jz and uniform positive scalar linear nonremanent constitutive law; BH exact whole-table linearity and recoil equal principal mu_r/zero remanence; original exterior material retained',
        sampling='N and 2N on R and 0.75R; primary N coefficients; negative/high orders, angular/radial differences and field remainder are diagnostics',
        source_binding='all five native file SHA256 values; original FEM and all Fourier traces replayed; no automatic source path lookup',
        project=False,gui=False,study=False,
        limits='planar straight linear/recoil P1/P2 and B-H P1 success native only; no failed/axisymmetric/curved source or nonlinear/anisotropic/remanent/current-bearing aperture; no force, torque, longitudinal integral or continuum error bound')


def planar_magnetic_force_capabilities():
    return dict(request_format='superfish_ng_planar_magnetic_force_request',request_schema_versions=[1],report_format='superfish_ng_planar_magnetic_force_report',report_schema_versions=[1,2],
        source_native_manifest_formats=['superfish_ng_planar_magnetostatic_manifest','superfish_ng_planar_bh_manifest','superfish_ng_planar_recoil_manifest'],source_native_schema_versions=[1],force_format='superfish_ng_planar_magnetic_force',force_schema_versions=[1,2],
        virtual_work_format='superfish_ng_planar_magnetic_virtual_work',virtual_work_schema_versions=[1,2],element_orders=[1,2],source_element_orders=dict(linear_scalar=[1,2],nonlinear_bh=[1],linear_recoil=[1,2]),
        commands=['analyze-planar-magnetic-force','replay-planar-magnetic-force'],force_unit='N/m',torque_unit='N m/m',
        scope='original scalar/B-H/recoil planar FEM; body w=1, exterior w=0, P1 weights [0,1]; all transitions declared vacuum with Jz=0; other current/nonvacuum regions w=0',
        torques=['scalar-weight moment of Maxwell stress','stress of P1 nodal rotation velocity, matched to actual displaced-FEM work'],
        virtual_work='explicit null or 2..8 decreasing positive translation/rotation steps; fixed exterior and integrated currents; recoil body tensors/remanence co-rotate; true constitutive potential minus J/Ht work; complete Cases, potentials and Newton histories retained',
        material_report_workflow_statuses=['complete','virtual_work_failed'],cli_exit_codes=dict(complete=0,retained_virtual_work_failure=1,invalid_or_io=2),
        source_binding='five native file SHA256 values and complete source FEM, stress, and optional actual displaced-FEM replay, including the same retained nonlinear failure',project=False,gui=False,study=False,
        limits='no failed source native, axisymmetric or curved source; no implicit length, RF factor, smoothing or continuum force/torque accuracy bound; scalar report version 1 remains unchanged')


def off_axis_magnetic_force_capabilities():
    return dict(request_format='superfish_ng_off_axis_magnetic_force_request',request_schema_versions=[1],report_format='superfish_ng_off_axis_magnetic_force_report',report_schema_versions=[1],
        source_native_manifest_format='superfish_ng_off_axis_magnetostatic_manifest',source_native_schema_versions=[1],force_format='superfish_ng_off_axis_magnetic_force',force_schema_versions=[1],virtual_work_format='superfish_ng_off_axis_magnetic_virtual_work',virtual_work_schema_versions=[1],element_orders=[1,2],
        commands=['analyze-off-axis-magnetic-force','replay-off-axis-magnetic-force'],force_unit='N',force_component='z for the full annular body',potential_unit='J',current_unit='A from integral Jphi dr dz',
        scope='strictly positive-radius linear scalar original FEM; all weight gradients in declared vacuum mu_r=1,Jphi=0; body w=1, outer/hole boundaries and other sources/nonvacuum regions w=0',
        virtual_work='explicit null or 2..8 decreasing positive axial steps; radial coordinates, exterior and integrated azimuthal currents fixed; full displaced Cases, energy/source work and coefficient SHA retained',
        quadrature='source Case order q from 4..32, with q+4 stress comparison; no quadrature-error bound',source_binding='all five native SHA256 values and complete actual FEM/stress/optional axial-work replay',project=False,gui=False,study=False,
        limits='no planar N/m reinterpretation, radial net vector force, meridional torque, axis-connected/BH/recoil/curved or failed source, GUI or continuum force accuracy certification')
